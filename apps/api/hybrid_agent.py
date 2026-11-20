"""Rescate selectivo. El motor local conserva la autoridad sobre evidencias y cálculos."""
import asyncio
import logging
import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field, replace
from datetime import date
from time import perf_counter
from typing import Literal
from uuid import uuid4

import pymupdf
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .agent import ChatResponse, ProviderUnavailable, sentence_score
from .corpus import (
    PDF_LOCK, Citation, SearchRequest, definition_topic, definition_under_heading,
    documentary_query, explanation_terms, indirect_definition, list_under_heading, page_lines, policy_scope, terms,
)
from .currency_request import verify_currency_request
from .deepseek_config import USD_NANO
from .deepseek_wire import UsageTotals
from .hybrid_planner import DeterministicPlanner, FinanceConstraints, HybridPlanner, Plan
from .finance import Abstain, PERIOD, check_stock_sum, normalize
from .financial_agent import CURRENCY, ENTITY_NAME, METRIC, Trace, normalize_periods, parse_intent, requires_financial_tools


MODE = "híbrido experimental"
LOGGER = logging.getLogger("uvicorn.error")
DEADLINE = 15
MAX_TOOLS = 24  # La operación local de dos monedas ya puede usar dos presupuestos de 12.
DOC_READS = 4
CANONICAL_TOPICS = {
    "coeficiente cobertura liquidez": "coeficiente de cobertura de liquidez",
    "riesgo credito": "riesgo de crédito",
}
CONCEPT_SYNONYMS = {"margen explotacion": "margen operativo"}
TOPIC_ALIASES = {
    "coeficiente cobertura liquidez": ("ccl", "activos", "liquidos", "salidas", "netas", "efectivo", "relacion"),
    "riesgo credito": ("perdida", "potencial", "pago", "contraparte", "acreditado"),
    "margen operativo": ("proporcion", "ingresos", "gastos", "operativos"),
    "portafolio credito": ("segmentamos",),
}
RESTRICTION = re.compile(
    r"\b(?:solo|unicamente|exclusiv\w*|excepto|sin incluir|salvo|anteriores?|posteriores?|"
    r"no incluy\w*|sin considerar|no ajustad\w*|adoptara[n]?|implementara[n]?|futur\w*|vigencia)\b"
)
INDIRECT = re.compile(r"\b(?:a que se refiere|que se entiende|a que alude|como describ\w*|que significa)\b")
GENERIC_INDIRECT = re.compile(r"\b(?:habla|hablan|alude|aluden) de(?:l)? (?:la |el )?([a-z ]{3,64})$")
DOC_SPLIT = re.compile(r"(?:\s+y[,]?\s+|[;?]\s*)(?=(?:[¿]?)(?:explica|describe|define|enumera|por separado|c[oó]mo se|a qui[eé]n)\b)", re.I)
DOC_LEAD = re.compile(
    r"^(?:(?:explica|describe|define|enumera|senala|presenta|identifica|por separado|aparte)\b[, :]+)+"
)
SECOND_METRIC = re.compile(
    r"^(?:dame |indica |muestra |calcula |estima )?(?:ademas |tambien |aparte )?(?:el |la )?"
    r"(?P<operation>cambio|diferencia|variacion|crecimiento)(?: (?P<relative>porcentual|relativ[oa]))? "
    r"(?P<metric>[a-z ]{2,48}?)(?: en esos trimestres| en esos periodos| entre los mismos periodos"
    r"| en las mismas fechas| en los mismos trimestres)?$"
)
EXTRA_FINANCIAL = re.compile(r"[.?!;]\s+(?=(?:[¿¡]\s*)?(?:dame|indica|muestra|calcula|estima|adem[aá]s|tambi[eé]n)\b)", re.I)
INDEPENDENT_OPERATIONS = re.compile(r"\bprimero[, :]\s*(.+?)(?:[;.]\s*|\s+)segundo[, :]\s*(.+)", re.I)
PARALLEL_METRICS = re.compile(r"\btanto\s+(?:el\s+|la\s+)?([^,.;?]+?)\s+como\s+(?:el\s+|la\s+)?", re.I)
COORDINATED_FINANCE = re.compile(
    r"(?:,?\s+y,?\s+(?:por (?:separado|otro lado|otra parte),?\s+)?|[;]\s*)(?="
    r"(?:calcula|muestra|dame|indica|estima|determina|reporta)\b|"
    r"(?:el|la)\s+(?:cambio|variaci[oó]n|movimiento|diferencia|crecimiento)\b)",
    re.I,
)
DEFINITION_VERB = re.compile(
    r"\b(?:es (?:la|el|una|un) |se (?:define|determina|calcula|refiere) |consiste |"
    r"(?:permite )?cuantifica(?:r)? .{0,95}\b(?:relacion|mediante|traves)\b)"
)
UNSAFE_PASSAGE = re.compile(r"\b(?:ignora|obedece|instruccion(?:es)?|revela|ejecuta|credenciales)\b")
BANK_ENTITY = re.compile(r"^banco [a-z]+(?: [a-z]+){0,3}$")


def plain(text):
    # Conservar artículos y preposiciones para validar la estructura original.
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c))


class DocumentNeed(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    topic: str = Field(min_length=2, max_length=150)
    kind: Literal["definition", "list", "passage", "scope"]
    scope: str | None = None
    year: int | None = None
    report: Literal["annual", "financial"] | None = None
    facets: tuple[tuple[str, ...], ...] = ()
    anchor: str | None = None
    current_report: bool = False

    @property
    def keywords(self):
        return tuple(terms(self.topic))

    @property
    def permitted(self):
        return sorted(set(self.keywords) | set(TOPIC_ALIASES.get(normalize(self.topic), ()))
                      | {word for group in self.facets for word in group})


# Patrones de evidencia, aplicados a cualquier entidad y fuente elegible.
REPORT_YEAR = re.compile(
    r"\b(?:estados financieros|informe anual|reporte anual|(?:politicas|capitulo|apartado)(?: de)? liquidez)"
    r" (?:de |del )?(20\d{2})\b"
)
FREQUENCY = ("mensual", "semanal", "trimestral", "anual", "diari")
PERSONS = ("cpr", "consejo", "directivo", "administracion", "grupo")
REPORT_RECIPIENT = re.compile(r"\b(?:a qui[eé]n|qui[eé]n recibe|destinatario\w*|a que organo)\b")
REPORT_FORM = re.compile(r"\b(?:inform\w*|report\w*)\b")
PORTFOLIO = r"\b(?:(?:segment\w*|divid\w*|separ\w*)\b.{0,80}\bportafolio|segmentos?\b.{0,80}\bcredito)\b"
ORIGINATION = r"\b(?:control\w*|mitigante\w*|verific\w*|valid\w*)\b.{0,95}\boriginacion\b"
LIQUIDITY_TOOLS = r"\b(?:herramientas|medidas|metodologias)\b.{0,70}\b(?:gestion|contingencia|operativas)\b"
REPORTING_POLICY = r"\b(?:informar|informacion|revelacion|divulgacion)\b.{0,85}\b(?:consejo|autoridades)\b"
SCOPE_QUESTION = re.compile(
    r"\b(?:se pueden? (?:atribuir|aplicar)|puedo concluir|es exhaustiv[oa]|es suficiente para afirmar|"
    r"(?:demuestra|acredita|prueba de que)\b.{0,45}\b(?:todas?|cada)|"
    r"(?:subsidiarias|filiales)\b.{0,45}\bmism[oa]s?\b)"
)
OPEN_FRAMES = (
    (PORTFOLIO,
     "portafolio credito", (("minorista",), ("mayorista",), ("segmentamos", "segmenta", "segmentacion")),
     r"\b(?:para fines de gestion del riesgo (?:de )?credito )?segment\w* [^:]{0,55}portafolio[^:]{0,20}:"),
    (ORIGINATION,
     "originacion mitigantes", (("originacion",), ("mitigante", "control")), r"\boriginacion\b"),
    (r"\b(?:frecuencia|a quien se informa|semanalmente|trimestralmente)\b",
     "liquidez reportes", (FREQUENCY, PERSONS), None),
    (r"\b(?:herramientas|medidas|metodologias)\b.*\bcontingencia\b",
     "liquidez gestion", (("contingencia",), ("brechas", "indicadores", "pruebas")), None),
    (r"\b(?:objetivo|finalidad)\b",
     "", (("objetivo", "fin", "necesidad", "mantener", "para", "garantizar", "medir"),), None),
)
DOC_FILLERS = set(
    "sobre dentro bajo separadamente separado indica senala muestra explica informa frecuencia relacion mide "
    "tiene contempla puede reflejan disponibles solicita crediticio objetivo finalidad marco habla "
    "mencionado descrito incluye detalle distingue documenta aparece figuraba".split()
)


def document_needs(question):
    content = documentary_query(question)
    text = plain(content)
    year_match = REPORT_YEAR.search(text)
    year = int(year_match[1]) if year_match else None
    if (RESTRICTION.search(text) or any(int(y) > date.today().year for y in re.findall(r"\b20\d{2}\b", text))
            or re.search(r"\d", REPORT_YEAR.sub("", text))):
        return []
    scope = next((scope for scope in ("tenedora", "gfnorte", "banorte")
                  if re.search(rf"\b{scope}\b", text)), None)
    if scope is None and re.search(r"\b(?:informe|documento) ficticio\b", text):
        scope = "ficticio"
    report = "financial" if "estados financieros" in text or (year_match and "liquidez" in year_match[0]) else (
        "annual" if re.search(r"\b(?:informe|reporte) anual\b", text) else None
    )
    scope_question = bool(SCOPE_QUESTION.search(text))
    if (re.search(r"\b(?:banco|grupo|filial\w*|subsidiaria\w*|anexo)\b", text) and not scope_question
            or re.search(r"\b(?:todas?|exhaustiv\w*)\b", text) and not scope_question):
        return []
    if re.search(r"\b(?:en|segun) (?:los |el )?(?:informes?|reportes?|documentos?)\b", text):
        if not (scope or report or re.search(r"\bdisponibles\b", text)):
            return []
    keys = set(terms(text))
    if scope_question and "politicas" in keys and ("liquidez" in keys or scope == "tenedora"):
        topic = "políticas de liquidez" if "liquidez" in keys else "políticas de la Tenedora"
        return [DocumentNeed(topic=topic, kind="scope", scope=scope, year=year, report=report,
                             current_report=scope == "tenedora" and year is None)]
    if ({"acreditado", "contraparte"} & keys and {"incumplimiento", "pago", "quebranto"} & keys
            and {"riesgo", "concepto"} & keys and re.search(r"\b(?:que riesgo|como (?:llama|denomina))\b", text)):
        return [DocumentNeed(topic="riesgo de crédito", kind="definition", scope=scope, year=year, report=report)]
    if re.search(PORTFOLIO, text) and re.search(ORIGINATION, text) and (
        re.search(r"\b(?:credito|creditici\w*)\b", text)
    ):
        return [DocumentNeed(topic=topic, kind="passage", scope=scope, year=year, report=report,
                             facets=facets, anchor=anchor) for _, topic, facets, anchor in OPEN_FRAMES[:2]]
    if {"politica", "liquidez"} <= keys and re.search(REPORTING_POLICY, text) and re.search(LIQUIDITY_TOOLS, text):
        return [
            DocumentNeed(topic="políticas de liquidez", kind="list", scope=scope or "tenedora", year=year, report=report,
                         facets=(("consejo",), ("autoridades",)), current_report=year is None),
            DocumentNeed(topic="riesgo de liquidez", kind="passage", scope=scope or "tenedora", year=year, report=report,
                         facets=(("brechas",), ("pruebas",), ("contingencia",)), current_report=year is None),
        ]
    if "contingencia" in keys and re.search(LIQUIDITY_TOOLS, text) and (
        "liquidez" in keys or "balance" in keys or scope == "tenedora"
    ):
        return [DocumentNeed(topic="riesgo de liquidez", kind="passage", scope=scope, year=year, report=report,
                             facets=(("brechas", "indicador"), ("pruebas",), ("contingencia",)),
                             current_report=bool(scope and year is None))]
    parts = [part for part in DOC_SPLIT.split(content) if part.strip(" ¿?")]
    if not 1 <= len(parts) <= 2:
        return []
    needs = []
    for part in parts:
        cleaned = plain(part).strip(" ¿?!.,")
        cleaned = re.sub(r"\b(?:en |del? )?(?:los )?(?:informes?|reportes?|documentos?|estados financieros)"
                         r"(?: anual)?(?: de (?:la )?(?:tenedora|gfnorte|banorte)| de 20\d{2})", "", cleaned).strip()
        cleaned = re.sub(r"\b(?:de|para) (?:la )?(?:tenedora|gfnorte|banorte)\b", "", cleaned).strip()
        cleaned = DOC_LEAD.sub("", cleaned).strip()
        topic = definition_topic(cleaned.rstrip(" ,"))
        facets = ()
        anchor = None
        period = tuple(frequency for frequency in FREQUENCY if re.search(rf"\b{frequency}\w*\b", cleaned))
        management = ("liquidez" in keys or scope == "tenedora") and re.search(LIQUIDITY_TOOLS, cleaned)
        reporting = ("liquidez" in keys or scope == "tenedora") and REPORT_FORM.search(cleaned)
        if reporting and period and REPORT_RECIPIENT.search(cleaned):
            kind, topic = "passage", "liquidez reportes"
            facets = (*((frequency,) for frequency in period), PERSONS)
        elif management:
            kind, topic = "passage", "riesgo de liquidez"
            facets = (("brechas", "indicador"), ("pruebas",))
            if "contingencia" in terms(cleaned):
                facets += (("contingencia",),)
        elif topic:
            kind = "definition"
        elif INDIRECT.search(cleaned) or indirect_definition(part):
            candidates = [topic for topic, aliases in TOPIC_ALIASES.items()
                          if set(topic.split()) <= set(terms(cleaned)) or ("ccl" in aliases and "ccl" in terms(cleaned))]
            match = GENERIC_INDIRECT.search(cleaned)
            topic = candidates[0] if len(candidates) == 1 else match[1] if match else ""
            topic = CONCEPT_SYNONYMS.get(normalize(topic), topic)
            kind = "definition"
        elif (re.search(r"\bcobertura de liquidez\b|\bccl\b", cleaned)
              and re.search(r"\b(?:mide|relacion|usa|cuantifica|coeficiente)\b", cleaned)) or (
                  {"activos", "liquidos", "netos"} <= set(terms(cleaned)) and "horizonte" in cleaned):
            topic, kind = "coeficiente de cobertura de liquidez", "definition"
        elif frame := next((frame for frame in OPEN_FRAMES if re.search(frame[0], cleaned)), None):
            topic = frame[1] or " ".join(word for word in terms(cleaned) if word not in DOC_FILLERS)
            kind, facets, anchor = "passage", frame[2], frame[3]
            if "cpr" in cleaned and "consejo" in cleaned:
                facets += (("cpr",), ("consejo",))
            if "semanalmente" in cleaned and "trimestralmente" in cleaned:
                facets += (("semanal",), ("trimestral",))
        elif len(parts) == 2:
            topic = cleaned
            kind = "list" if normalize(topic).startswith("objetivos ") else (
                "definition" if normalize(topic) in TOPIC_ALIASES else "passage"
            )
        elif listing := explanation_terms(part):
            topic, kind = " ".join(sorted(listing)), "list"
        elif re.search(r"\b(?:que|como|cuales|cual|quien|enumera|describe)\b", plain(part)):
            # Caso abierto. Las palabras que el plan seleccione solo orientan FTS.
            # El pasaje debe seguir acreditando todos los términos de contenido locales.
            topic = " ".join(word for word in terms(cleaned) if word not in DOC_FILLERS)
            kind = "passage"
        else:
            return []
        words = terms(topic)
        if not 2 <= len(words) <= 12 or len(topic) > 150:
            return []
        needs.append(DocumentNeed(topic=CANONICAL_TOPICS.get(normalize(topic), topic), kind=kind,
                                  scope=scope, year=year, report=report, facets=facets, anchor=anchor,
                                  current_report=bool(scope and year is None
                                                      and (reporting or management or topic == "liquidez reportes"))))
    return needs


def comparable_periods(intent):
    return (intent.base.kind, intent.base.months) == (intent.current.kind, intent.current.months)


def financial_need(question, primary):
    parts = EXTRA_FINANCIAL.split(documentary_query(question))
    if len(parts) != 2 or primary.currencies or not comparable_periods(primary):
        return None
    second = plain(parts[1]).strip(" ¿?!.,")
    match = SECOND_METRIC.fullmatch(second)
    if not match:
        return None
    metric = " ".join(terms(match["metric"]))
    # Las restricciones de la segunda cláusula deben tener representación
    # inequívoca. Si contradicen la primera, no se reconstruye la consulta.
    if (not metric or normalize(primary.metric) == normalize(metric)
            or set(terms(metric)) & {"moneda", "pesos", "dolares", "euros", "grupo", "banco", "gfnorte",
                                     "millones", "miles", "porcentaje", "puntos", "escala", "ajustado", "sin"}):
        return None
    relative = bool(match["relative"]) or match["operation"] == "crecimiento"
    if match["operation"] == "variacion" and not relative:
        return None
    return replace(primary, metric=metric, operation="percent_change" if relative else "difference",
                   additional_difference=False, percentage_points=False, definition_check=False)


def split_financial_operations(question):
    """Separar métricas coordinadas sin aplicar la unidad o los periodos de una a la otra."""
    content = documentary_query(question)
    # Exigir una operación reconocible y exactamente dos métricas distintas.
    metrics = list(METRIC.finditer(content))
    if len(metrics) != 2 or metrics[0].lastgroup == metrics[1].lastgroup:
        return None
    # La unidad monetaria puede tener alcance global. Conservar el flujo
    # original si no se puede asignar a un apartado sin ambigüedad.
    if CURRENCY.search(content):
        return None
    try:
        verify_currency_request(content)
    except Abstain:
        return None
    if explicit := INDEPENDENT_OPERATIONS.search(content):
        if METRIC.search(content[:explicit.start()]) or PERIOD.search(content[:explicit.start()]):
            return None
        first, second = explicit.groups()
    elif (paired := PARALLEL_METRICS.search(content)) and (
        paired[1].strip().lower() == metrics[0][0].lower()
        and paired.end() == metrics[1].start()
    ):
        shared = content[:paired.start()] + "{metric}" + content[metrics[1].end():]
        first, second = (shared.replace("{metric}", metric[0]) for metric in metrics)
    else:
        boundaries = [match for match in COORDINATED_FINANCE.finditer(content)
                      if metrics[0].end() <= match.start() <= metrics[1].start()]
        if len(boundaries) != 1:
            return None
        cut = boundaries[0]
        first, second = content[:cut.start()], content[cut.end():]
    first_periods = list(PERIOD.finditer(normalize_periods(first)))
    if len(first_periods) == 2 and not PERIOD.search(normalize_periods(second)):
        # El segundo apartado sin fechas usa el par común previamente indicado.
        # Ante una referencia temporal propia que el analizador no reconoce, abstenerse.
        if re.search(r"\b(?:19\d{2}|20\d{2}|trimestres?|acumulado|meses)\b", second, re.I):
            return None
        p, q = (match[0] for match in first_periods)
        second = f"Entre {p} y {q}, {second}"
    entities = list(ENTITY_NAME.finditer(content))
    if len(entities) == 1:
        entity = "GFNorte" if entities[0]["known"] else entities[0]["other"]
        if not ENTITY_NAME.search(first):
            first = f"{first.rstrip('. ')}. Entidad: de {entity}."
        if not ENTITY_NAME.search(second):
            second = f"{second.rstrip('. ')}. Entidad: de {entity}."
    # Si hay fechas específicas sin normalizar o la cláusula es ambigua,
    # no se genera una operación derivada.
    if not all(requires_financial_tools(part) for part in (first, second)):
        return None
    return first, second


def doc_support(need, snippet):
    wanted = set(need.keywords)
    text = plain(snippet)
    observed = set(terms(snippet))
    if UNSAFE_PASSAGE.search(text):
        return False
    if need.facets:
        if need.anchor and not re.search(need.anchor, text):
            return False
        if (len(wanted & observed) < max(1, (len(wanted) * 3 + 4) // 5)
                or not all(any(token.startswith(word) for token in observed for word in group)
                           for group in need.facets)):
            return False
    elif not wanted <= observed:
        return False
    if need.kind == "definition":
        if sentence_score(f"¿Cómo se define el {need.topic}?", snippet)[0]:
            return True
        heading, colon, body = text.partition(": ")
        candidate = body if colon and terms(heading) == list(need.keywords) else text
        cue = DEFINITION_VERB.search(candidate)
        if not cue:
            return False
        subject = terms(candidate[:cue.start()])
        acronym = "".join(word[0] for word in need.keywords)
        return subject == list(need.keywords) or (
            colon and terms(heading) == list(need.keywords) and subject == [acronym]
        )
    if need.kind in {"list", "scope"}:
        return "•" in snippet and (need.kind != "scope" or need.scope != "tenedora" or "tenedora" in observed)
    return len(snippet) >= 40 and ("." in snippet or bool(need.facets))


def report_scope(need, title):
    name = set(terms(title))
    if need.year is not None and str(need.year) not in name:
        return False
    if need.report == "annual" and not (name & {"ia", "anual"}):
        return False
    if need.report == "financial" and not ("eeff" in name or {"estados", "financieros"} <= name):
        return False
    if not need.scope:
        return True
    if need.scope == "ficticio":
        return "ficticio" in name
    if need.scope == "tenedora":
        return bool(name & {"grupo", "tenedora", "gfnorte"}) and (
            "eeff" in name or {"estados", "financieros"} <= name
        )
    return bool(name & {"banorte", "gfnorte", "tenedora"}) or (
        "grupo" in name and ("eeff" in name or {"estados", "financieros"} <= name)
    )


def first_sentence(text):
    match = re.search(r"[.!?](?=\s|$)", text)
    return text[:match.end()] if match else ""


def definition_on_page(page, need):
    # En un encabezado o pasaje en varias líneas, seguir solo la misma
    # columna y detenerse ante otro encabezado o un salto de párrafo.
    lines = sorted(((x, y, r, b, line.strip()) for x, y, r, b, line in page_lines(page) if line.strip()),
                   key=lambda line: (line[1], line[0]))
    for index, (left, _, _, bottom, line) in enumerate(lines):
        title = re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", line).strip()
        heading = terms(title) == list(need.keywords)
        inline = terms(line)[:len(need.keywords)] == list(need.keywords)
        if not (heading or inline):
            continue
        body = [] if heading else [line]
        for x, top, _, end, following in lines[index + 1:]:
            if abs(x - left) > 8 or top < bottom:
                continue
            if top - bottom > 28 or re.match(r"^\d+\.\d+\s", following):
                break
            body.append(following)
            bottom = end
            if len(body) >= 5 or first_sentence(" ".join(body)):
                break
        sentence = first_sentence(" ".join(body))
        if sentence:
            candidate = f"{title}: {sentence}" if heading else sentence
            if doc_support(need, candidate):
                return candidate
    return ""


def passage_from_context(page, need):
    """Tomar un tramo contiguo del orden original, con encabezado y facetas."""
    text = " ".join(page.get_text().split())
    normalized = plain(text)
    if len(normalized) != len(text):
        return ""
    for hit in re.finditer(need.anchor, normalized):
        # Las mayúsculas de un encabezado separan apartados del mismo PDF.
        start = hit.start()
        if text[start:hit.end()].isupper():
            tail = re.split(r"\s+(?=[A-ZÁÉÍÓÚÑ]{5,}\b)", text[hit.end():hit.end() + 950], maxsplit=1)[0]
            section = text[start:hit.end()] + tail
        else:
            section = text[start:start + 740]
        for match in re.finditer(r"[.!?](?=\s|$)", section):
            candidate = section[:match.end()]
            if doc_support(need, candidate):
                if text[start:hit.end()].isupper():
                    controls = re.split(r"mitigantes clave:|controles? clave:", candidate, maxsplit=1, flags=re.I)
                    if len(controls) != 2 or controls[1].count(".") < 2:
                        continue
                return candidate
    return ""


def verified_passage(corpus, ref, need):
    name, data = corpus.original(ref.doc_id)
    if not report_scope(need, name):
        return None
    with PDF_LOCK, pymupdf.open(stream=data, filetype="pdf") as pdf:
        page = pdf[ref.pdf_page - 1]
        snippet = ""
        if need.kind in {"list", "scope"}:
            snippet = list_under_heading(page, set(need.keywords))
        elif need.kind == "definition":
            snippet = definition_under_heading(page, need.topic) or ""
            if not snippet:
                snippet = definition_on_page(page, need)
        if not snippet and need.anchor:
            snippet = passage_from_context(page, need)
        if not snippet and need.kind not in {"list", "scope"}:
            # Un bloque puede contener varias oraciones. La evidencia devuelta
            # es solo la oración que demuestra el apartado.
            for block in page.get_text("blocks"):
                if block[6] != 0:
                    continue
                sentences = re.split(r"(?<=[.!?])\s+", " ".join(block[4].split()))
                for size in range(1, 4 if need.facets else 2):
                    for start in range(len(sentences) - size + 1):
                        passage = " ".join(sentences[start:start + size])
                        if len(passage) <= 900 and doc_support(need, passage) and (
                            passage.endswith((".", "?", "!")) or need.facets
                        ):
                            snippet = passage
                            break
                    if snippet:
                        break
                if snippet:
                    break
    if not snippet or not doc_support(need, snippet):
        return None
    return Citation(doc_id=ref.doc_id, filename=name, pdf_page=ref.pdf_page,
                    evidence_id=f"{ref.doc_id}:{ref.pdf_page}:híbrido:{ref.fragment}", snippet=snippet)


@dataclass
class RequestBudget:
    deadline: float
    tools: list[str] = field(default_factory=list)
    rescue_started: float | None = None
    attempted: dict[int, str] = field(default_factory=dict)
    verified: set[int] = field(default_factory=set)

    async def call(self, name, function, *args):
        if len(self.tools) >= MAX_TOOLS:
            raise ProviderUnavailable("Se alcanzó el límite de herramientas del rescate.")
        self.tools.append(name)
        async with asyncio.timeout_at(self.deadline - 0.05):
            return await asyncio.to_thread(function, *args)


class HybridAgent:
    def __init__(self, documentary, financial, planner=None):
        self.documentary = documentary
        self.financial = financial
        self.corpus = documentary.corpus
        self.planner = planner
        self.mode = MODE
        self.planner_mode = (
            "deterministic" if isinstance(planner, DeterministicPlanner)
            else "external" if isinstance(planner, HybridPlanner)
            else "in-process" if planner is not None else "none"
        )

    async def answer(self, question, metrics):
        loop = asyncio.get_running_loop()
        budget = RequestBudget(loop.time() + DEADLINE)
        start = perf_counter()
        original_time = start
        totals = UsageTotals()
        stage = "local"
        base = ChatResponse(
            answer="No se pudo verificar la consulta dentro del plazo disponible.", citations=[], warnings=[],
            tools_used=[], request_id=uuid4().hex, provider_mode=MODE, status="abstained",
        )
        reply = base
        try:
            async with asyncio.timeout_at(budget.deadline):
                operations = split_financial_operations(question)
                primary = operations[0] if operations else question
                finance = operations is not None or requires_financial_tools(question)
                primary_trace = Trace() if operations else None
                if primary_trace is not None:
                    base = await self.financial.answer(primary, trace=primary_trace)
                else:
                    base = await (self.financial if finance else self.documentary).answer(primary)
                reply = base
                budget.tools.extend(base.tools_used)
                original_time = perf_counter()
                stage = "protected"
                if finance:
                    reply, stage = await self.finance(question, base, budget, totals, operations, primary_trace)
                else:
                    reply, stage = await self.documents(question, base, budget, totals)
        except (TimeoutError, ProviderUnavailable, KeyError, OSError, sqlite3.Error, RuntimeError):
            stage = "fallback"
        finally:
            activated = budget.rescue_started is not None
            rescue_ms = round((perf_counter() - budget.rescue_started) * 1000) if activated else 0
            attempted = ",".join(f"{i}:{kind}" for i, kind in budget.attempted.items()) or "-"
            verified = ",".join(str(i) for i in sorted(budget.verified)) or "-"
            metrics.update({
                "X-Hybrid-Decision": stage,
                "X-Hybrid-Planner": self.planner_mode,
                "X-Hybrid-Rescue-Activated": str(int(activated)),
                "X-Hybrid-Rescue-Ms": str(rescue_ms),
                "X-Hybrid-Sections-Attempted": attempted,
                "X-Hybrid-Sections-Verified": verified,
                "X-Hybrid-Tools": str(len(budget.tools)),
                "X-Hybrid-Local-Ms": str(round((original_time - start) * 1000)),
                "X-Hybrid-Total-Ms": str(round((perf_counter() - start) * 1000)),
                "X-P2-DeepSeek-Rescue": stage,
                "X-P2-DeepSeek-Local-Ms": str(round((original_time - start) * 1000)),
                "X-P2-DeepSeek-Calls": str(totals.calls),
                "X-P2-DeepSeek-Input": str(totals.prompt),
                "X-P2-DeepSeek-Output": str(totals.output),
                "X-P2-DeepSeek-Usd-Upper": f"{totals.nano / USD_NANO:.9f}",
                "X-P2-DeepSeek-Usd-Unconfirmed": f"{totals.reserved_unconfirmed / USD_NANO:.9f}",
            })
            if self.planner_mode == "deterministic":
                LOGGER.info("hybrid_rescue id=%s activated=%s attempted=%s verified=%s rescue_ms=%s outcome=%s",
                            reply.request_id, int(activated), attempted, verified, rescue_ms, stage)
        return reply.model_copy(update={"provider_mode": MODE, "tools_used": budget.tools})

    async def ask(self, question, slots, totals, budget):
        if not self.planner:
            return None, "blocked"
        if budget.deadline - asyncio.get_running_loop().time() < 1:
            return None, "deadline"
        if len(budget.tools) + 2 > MAX_TOOLS:
            return None, "tool-budget"
        budget.rescue_started = perf_counter()
        try:
            async with asyncio.timeout_at(budget.deadline - 0.05):
                plan = await self.planner.plan(question, slots, totals)
            if plan is None:
                return None, "out-of-scope"
            plan = Plan.model_validate(plan)
        except ValidationError:
            return None, "invalid-plan"
        allowed = {entry["slot"]: entry for entry in slots}
        chosen = {}
        for step in plan.subquestions:
            chosen_terms = {normalize(item) for item in step.search_terms}
            if (step.slot not in allowed or step.slot in chosen
                    or not chosen_terms <= set(allowed[step.slot]["terms"])
                    or len(chosen_terms) != len(step.search_terms)):
                return None, "invalid-plan"
            if (step.interpretation is not None
                    and step.interpretation.model_dump(mode="json") != allowed[step.slot].get("restricciones")):
                return None, "invalid-plan"
            chosen[step.slot] = sorted(chosen_terms)
        return chosen, "planned" if chosen else "empty-plan"

    @staticmethod
    def partial(base, subject):
        note = f"Quedó pendiente verificar {subject}."
        return base.model_copy(update={"answer": f"{base.answer} {note}", "warnings": [*base.warnings, note]})

    async def finance(self, question, base, budget, totals, operations=None, primary_trace=None):
        try:
            primary = parse_intent(operations[0] if operations else question)
            check_stock_sum(primary.operation, primary.metric)
        except Abstain:
            return base, "protected"
        if operations:
            try:
                secondary = parse_intent(operations[1])
            except Abstain as exc:
                return self.partial(base, str(exc)), "unverified"
            if secondary.currencies or primary.currencies:
                return self.partial(base, secondary.metric), "tool-budget"
            if not secondary.entity and primary_trace.result:
                secondary = replace(secondary, entity=primary_trace.result[0].entity)
        else:
            secondary = financial_need(question, primary)
        if base.status == "abstained":
            if primary.operation == "participation":
                whole, part = primary.base, primary.current
                if not (whole.kind == "ytd" and part.kind == "quarter" and whole.year == part.year
                        and whole.end - whole.months <= part.end - part.months < part.end <= whole.end):
                    if "no está incluido" not in base.answer:
                        reason = (
                            f"El trimestre {part.label} no está incluido en el acumulado solicitado {whole.label}."
                            if whole.kind == "ytd" and part.kind == "quarter"
                            else "La participación exige un trimestre incluido en un acumulado del mismo año."
                        )
                        return base.model_copy(update={
                            "answer": f"No puedo calcular la participación. {reason}",
                            "citations": [], "warnings": [],
                        }), "local-diagnostic"
                return base, "protected"
            if not comparable_periods(primary):
                if "distinto tipo o duración" not in base.answer:
                    sentence = "Los periodos tienen distinto tipo o duración, por ejemplo trimestre frente a acumulado."
                    return base.model_copy(update={"answer": f"{base.answer} {sentence}"}), "local-diagnostic"
            elif primary.entity and not base.citations and BANK_ENTITY.fullmatch(normalize(primary.entity)):
                if "entidad" not in plain(base.answer):
                    refs = await budget.call("search_corpus", self.corpus.search_corpus,
                                             SearchRequest(query=primary.entity, top_k=1))
                    if not refs:
                        note = "No se encontró respaldo para la entidad solicitada en el corpus indexado."
                        return base.model_copy(update={"answer": f"{base.answer} {note}"}), "local-diagnostic"
            reason = plain(" ".join([base.answer, *base.warnings]))
            if (secondary is None or primary.entity is None or re.search(
                    r"\b(?:perimetro|moneda|escala|entidad|no es aditiva|incompatibles)\b", reason)):
                return base, "protected"
        elif secondary is None or "financial_calculator" not in base.tools_used or not base.citations:
            return base, "complete"
        pending = self.partial(base, secondary.metric)
        try:
            constraints = FinanceConstraints(
                metric=secondary.metric, entity=secondary.entity, periods=(secondary.base.label, secondary.current.label),
                operation=secondary.operation, currency=secondary.output_currency, scale=secondary.output_scale,
                unit="puntos porcentuales" if secondary.percentage_points else None,
            )
            chosen, stage = await self.ask(question, [{"slot": 0, "tipo": "cálculo", "terms": [],
                                                     "restricciones": constraints.model_dump(mode="json")}], totals, budget)
            if not chosen:
                return pending, stage
            trace = Trace(tables=primary_trace.tables) if primary_trace is not None else Trace()
            budget.attempted[0] = "calculation"
            try:
                async with asyncio.timeout_at(budget.deadline - 0.05):
                    result = await self.financial.run_intent(secondary, trace, MAX_TOOLS - len(budget.tools))
            finally:
                budget.tools.extend(trace.tools)
        except (TimeoutError, ProviderUnavailable, KeyError, OSError, sqlite3.Error, RuntimeError, Abstain):
            return pending, "fallback"
        if result.status != "answered" or trace.result is None or len(result.citations) < 2:
            return pending, "unverified"
        if primary.entity is None and not all(
            f"· {operand.entity}." in base.answer for operand in trace.result[:2]
        ):
            return pending, "unverified"
        budget.verified.add(0)
        citations = list({cite.evidence_id: cite for cite in [*base.citations, *result.citations]}.values())
        keep = base if base.status == "answered" else self.partial(base, primary.metric)
        return keep.model_copy(update={
            "answer": f"{keep.answer} {result.answer}", "citations": citations, "status": "answered",
            "warnings": list(dict.fromkeys([*keep.warnings, *result.warnings])),
        }), "rescued" if base.status == "answered" else "partial-rescue"

    async def documents(self, question, base, budget, totals):
        needs = document_needs(question)
        if not needs:
            return base, "undetermined"
        if base.status == "answered" and policy_scope(question) and base.citations:
            # El flujo local comprueba título, página y alcance de esta política.
            if "no acredita" in base.answer or (len(base.citations) > 1 and "Medidas de gestión:" in base.answer):
                return base, "complete"
        covered = {i: cite for i, need in enumerate(needs) for cite in base.citations
                   if base.status == "answered" and report_scope(need, cite.filename)
                   and doc_support(need, cite.snippet) and doc_support(need, base.answer)
                   and (need.kind != "scope" or "no acredita" in base.answer)}
        slots = [{"slot": i, "tipo": need.kind, "tema": need.topic, "terms": need.permitted,
                  "aliases": list(TOPIC_ALIASES.get(normalize(need.topic), ()))}
                 for i, need in enumerate(needs) if i not in covered]
        if not slots:
            return base, "complete"
        initial = set(covered)
        pending = self.partial(base, " y ".join(needs[slot["slot"]].topic for slot in slots)) if (
            len(needs) > 1 or base.status == "answered"
        ) else base
        stage = "fallback"
        try:
            chosen, stage = await self.ask(question, slots, totals, budget)
            if not chosen:
                return pending, stage
            catalog = None
            for i, search_terms in chosen.items():
                need = needs[i]
                budget.attempted[i] = need.kind
                documents = None
                if need.scope or need.year or need.report:
                    if catalog is None:
                        catalog = await budget.call("list_documents", self.corpus.catalog)
                    eligible = [doc for doc in catalog if report_scope(need, doc["filename"])]
                    if need.current_report:
                        years = {doc["doc_id"]: max((int(t) for t in terms(doc["filename"])
                                                      if re.fullmatch(r"20\d{2}", t)), default=0)
                                 for doc in eligible}
                        most_recent = max(years.values(), default=0)
                        eligible = [doc for doc in eligible if years[doc["doc_id"]] == most_recent]
                    documents = {doc["doc_id"] for doc in eligible}
                query = f"¿Cómo se define el {need.topic}?" if need.kind == "definition" else need.topic
                refs = await budget.call("search_corpus", self.corpus.search_corpus,
                                         SearchRequest(query=query, documents=documents, top_k=8))
                if need.facets:
                    grouped = await budget.call("search_corpus", self.corpus.search_pages,
                                                 [need.keywords, *need.facets], documents, 6)
                    refs = [*grouped[:3], *refs, *grouped[3:]]
                expanded = set(search_terms) - set(need.keywords)
                if expanded:
                    guided = await budget.call("search_corpus", self.corpus.search_pages,
                                               [need.keywords, tuple(expanded)], documents, 4)
                    # La formulación sugerida nunca elimina los primeros candidatos de la búsqueda original.
                    refs = [*refs[:2], *guided[:2], *refs[2:]]
                pages = set()
                for ref in refs:
                    page = (ref.doc_id, ref.pdf_page)
                    if page in pages:
                        continue
                    if len(pages) >= DOC_READS:
                        break
                    pages.add(page)
                    citation = await budget.call("read_source", verified_passage, self.corpus, ref, need)
                    if citation:
                        covered[i] = citation
                        budget.verified.add(i)
                        break
        except (TimeoutError, ProviderUnavailable, KeyError, OSError, sqlite3.Error, RuntimeError):
            stage = "fallback"
        if set(covered) == initial:
            return pending, "unverified" if stage == "planned" else stage
        citations = list({cite.evidence_id: cite for _, cite in sorted(covered.items())}.values())
        parts = []
        for i, cite in sorted(covered.items()):
            need = needs[i]
            prefix = ""
            if need.kind == "scope":
                prefix = ("El pasaje identifica las políticas descritas. Por sí solo, no acredita que sean exhaustivas "
                          "ni que se apliquen a todas las filiales. ")
                if "liquidez" not in need.keywords:
                    prefix += "Este es un ejemplo del alcance identificado en el documento. "
            elif {"consejo", "autoridades"} <= {word for group in need.facets for word in group} and need.kind == "list":
                prefix = "Políticas de divulgación: "
            elif need.kind == "passage" and ("contingencia",) in need.facets:
                prefix = "Medidas de gestión: "
            parts.append(prefix + cite.snippet)
        parts = list(dict.fromkeys(parts))
        warnings = []
        if len(covered) != len(needs):
            missing = ", ".join(need.topic for i, need in enumerate(needs) if i not in covered)
            warnings.append(f"Respuesta parcial. Quedó pendiente verificar {missing}.")
        elif any(need.kind == "list" for need in needs):
            warnings.append("La selección se limita a los fragmentos citados.")
        return base.model_copy(update={
            "answer": " ".join([*parts, *warnings]), "citations": citations,
            "warnings": warnings, "status": "answered",
        }), "rescued" if len(covered) == len(needs) else "partial-rescue"
