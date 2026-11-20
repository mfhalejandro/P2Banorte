"""Rescate selectivo. El motor local conserva la autoridad sobre evidencias y cálculos."""
import asyncio
import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field, replace
from datetime import date
from time import perf_counter
from typing import Literal
from uuid import uuid4

import pymupdf
from pydantic import BaseModel, ConfigDict, Field

from .agent import ChatResponse, ProviderUnavailable, sentence_score
from .corpus import (
    PDF_LOCK, Citation, SearchRequest, definition_topic, definition_under_heading,
    documentary_query, indirect_definition, list_under_heading, page_lines, policy_scope, terms,
)
from .deepseek_config import USD_NANO
from .deepseek_wire import UsageTotals
from .hybrid_planner import FinanceConstraints
from .finance import Abstain, check_stock_sum, normalize
from .financial_agent import Trace, parse_intent, requires_financial_tools


MODE = "híbrido experimental"
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
}
RESTRICTION = re.compile(
    r"\b(?:solo|unicamente|exclusiv\w*|excepto|sin incluir|salvo|anteriores?|posteriores?|"
    r"no incluy\w*|sin considerar|no ajustad\w*|adoptara[n]?|implementara[n]?|futur\w*|vigencia)\b"
)
INDIRECT = re.compile(r"\b(?:a que se refiere|que se entiende|a que alude|como describ\w*|que significa)\b")
GENERIC_INDIRECT = re.compile(r"\b(?:habla|hablan|alude|aluden) de(?:l)? (?:la |el )?([a-z ]{3,64})$")
DOC_SPLIT = re.compile(r"(?:\s+y[,]?\s+|[;?]\s*)(?=(?:[¿]?)(?:explica|describe|define|enumera|por separado|c[oó]mo se|a qui[eé]n)\b)", re.I)
SECOND_METRIC = re.compile(
    r"^(?:dame |indica |muestra |calcula |estima )?(?:ademas |tambien |aparte )?(?:el |la )?"
    r"(?P<operation>cambio|diferencia|variacion|crecimiento)(?: (?P<relative>porcentual|relativ[oa]))? "
    r"(?P<metric>[a-z ]{2,48}?)(?: en esos trimestres| en esos periodos| entre los mismos periodos"
    r"| en las mismas fechas| en los mismos trimestres)?$"
)
EXTRA_FINANCIAL = re.compile(r"[.?!;]\s+(?=(?:[¿¡]\s*)?(?:dame|indica|muestra|calcula|estima|adem[aá]s|tambi[eé]n)\b)", re.I)
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

    @property
    def keywords(self):
        return tuple(terms(self.topic))

    @property
    def permitted(self):
        return sorted(set(self.keywords) | set(TOPIC_ALIASES.get(normalize(self.topic), ()))
                      | {word for group in self.facets for word in group})


# Patrones de evidencia, aplicados a cualquier entidad y fuente elegible.
REPORT_YEAR = re.compile(r"\b(?:estados financieros|informe anual|reporte anual) (?:de |del )?(20\d{2})\b")
FREQUENCY = ("mensual", "semanal", "trimestral", "anual", "diari")
PERSONS = ("cpr", "consejo", "directivo", "administracion", "grupo")
OPEN_FRAMES = (
    (r"\b(?:segment\w*|segmentado)\b.*\bportafolio\b|\bsegmentos?\b.*\bcredito\b",
     "portafolio credito", (("minorista",), ("mayorista",), ("segment",)), r"\bsegment\w* [^:]{0,55}portafolio[^:]{0,20}:"),
    (r"\b(?:control\w*|mitigante\w*)\b.*\boriginacion\b",
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
    report = "financial" if "estados financieros" in text else (
        "annual" if re.search(r"\b(?:informe|reporte) anual\b", text) else None
    )
    scope_question = bool(re.search(r"\b(?:se pueden? (?:atribuir|aplicar)|puedo concluir|es exhaustiv[oa])\b", text))
    if (re.search(r"\b(?:banco|grupo|filial\w*|subsidiaria\w*|anexo)\b", text) and not scope_question
            or re.search(r"\b(?:todas?|exhaustiv\w*)\b", text) and not scope_question):
        return []
    if re.search(r"\b(?:en|segun) (?:los |el )?(?:informes?|reportes?|documentos?)\b", text):
        if not (scope or report or re.search(r"\bdisponibles\b", text)):
            return []
    parts = [part for part in DOC_SPLIT.split(content) if part.strip(" ¿?")]
    if not 1 <= len(parts) <= 2:
        return []
    needs = []
    for part in parts:
        cleaned = plain(part).strip(" ¿?!.,")
        cleaned = re.sub(r"\b(?:en |del? )?(?:los )?(?:informes?|reportes?|documentos?|estados financieros)"
                         r"(?: anual)?(?: de (?:la )?(?:tenedora|gfnorte|banorte)| de 20\d{2})", "", cleaned).strip()
        cleaned = re.sub(r"\b(?:de|para) (?:la )?(?:tenedora|gfnorte|banorte)\b", "", cleaned).strip()
        cleaned = re.sub(r"^(?:explica|describe|define|enumera|por separado) (?:aparte |por separado )?", "", cleaned).strip()
        topic = definition_topic(cleaned.rstrip(" ,"))
        facets = ()
        anchor = None
        if scope_question and {"politicas", "liquidez"} <= set(terms(text)):
            return [DocumentNeed(topic="políticas de liquidez", kind="scope", scope=scope, year=year, report=report)]
        if topic:
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
                                  scope=scope, year=year, report=report, facets=facets, anchor=anchor))
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
        return "•" in snippet and (need.kind != "scope" or not need.scope or need.scope in observed)
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
                finance = requires_financial_tools(question)
                base = await (self.financial if finance else self.documentary).answer(question)
                reply = base
                budget.tools.extend(base.tools_used)
                original_time = perf_counter()
                stage = "protected"
                if finance:
                    reply, stage = await self.finance(question, base, budget, totals)
                else:
                    reply, stage = await self.documents(question, base, budget, totals)
        except (TimeoutError, ProviderUnavailable, KeyError, OSError, sqlite3.Error, RuntimeError):
            stage = "fallback"
        finally:
            metrics.update({
                "X-Hybrid-Decision": stage,
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
        return reply.model_copy(update={"provider_mode": MODE, "tools_used": budget.tools})

    async def ask(self, question, slots, totals, budget):
        if not self.planner:
            return None, "blocked"
        if budget.deadline - asyncio.get_running_loop().time() < 1:
            return None, "deadline"
        if len(budget.tools) + 2 > MAX_TOOLS:
            return None, "tool-budget"
        async with asyncio.timeout_at(budget.deadline - 0.05):
            plan = await self.planner.plan(question, slots, totals)
        if plan is None:
            return None, "out-of-scope"
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

    async def finance(self, question, base, budget, totals):
        try:
            primary = parse_intent(question)
            check_stock_sum(primary.operation, primary.metric)
        except Abstain:
            return base, "protected"
        secondary = financial_need(question, primary)
        if base.status == "abstained":
            if primary.operation == "participation":
                whole, part = primary.base, primary.current
                if not (whole.kind == "ytd" and part.kind == "quarter" and whole.year == part.year
                        and whole.end - whole.months <= part.end - part.months < part.end <= whole.end):
                    if "no está incluido" not in base.answer:
                        note = "El trimestre no está incluido en el acumulado solicitado."
                        return base.model_copy(update={"answer": f"{base.answer} {note}"}), "local-diagnostic"
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
            trace = Trace()
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
        slots = [{"slot": i, "tipo": need.kind, "tema": need.topic, "terms": need.permitted}
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
                documents = None
                if need.scope or need.year or need.report:
                    if catalog is None:
                        catalog = await budget.call("list_documents", self.corpus.catalog)
                    documents = {doc["doc_id"] for doc in catalog if report_scope(need, doc["filename"])}
                query = f"¿Cómo se define el {need.topic}?" if need.kind == "definition" else need.topic
                refs = await budget.call("search_corpus", self.corpus.search_corpus,
                                         SearchRequest(query=query, documents=documents, top_k=8))
                if need.facets:
                    grouped = await budget.call("search_corpus", self.corpus.search_pages,
                                                 [need.keywords, *need.facets], documents, 6)
                    refs = [*grouped[:3], *refs, *grouped[3:]]
                expanded = set(search_terms) - set(need.keywords)
                if expanded:
                    guided = await budget.call("search_corpus", self.corpus.search_corpus,
                                               SearchRequest(query=" ".join([*need.keywords, *sorted(expanded)]),
                                                             documents=documents, top_k=4))
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
                        break
        except (TimeoutError, ProviderUnavailable, KeyError, OSError, sqlite3.Error, RuntimeError):
            stage = "fallback"
        if set(covered) == initial:
            return pending, "unverified" if stage == "planned" else stage
        citations = list({cite.evidence_id: cite for _, cite in sorted(covered.items())}.values())
        parts = [("El pasaje delimita las políticas descritas y no acredita su aplicación a todas las entidades. "
                  if needs[i].kind == "scope" else "") + cite.snippet for i, cite in sorted(covered.items())]
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
