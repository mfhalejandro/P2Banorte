"""Rescate selectivo. El motor local conserva la autoridad sobre evidencias y cálculos."""
import asyncio
import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field, replace
from time import perf_counter
from uuid import uuid4

import pymupdf

from .agent import ChatResponse, ProviderUnavailable, sentence_score
from .corpus import (
    PDF_LOCK, Citation, SearchRequest, definition_topic, definition_under_heading,
    documentary_query, list_under_heading, page_lines, terms,
)
from .deepseek_config import USD_NANO
from .deepseek_wire import UsageTotals
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
    r"no incluy\w*|sin considerar|no ajustad\w*|adoptara[n]?|implementara[n]?|futur\w*|todas?|exhaustiv\w*|vigencia)\b"
)
INDIRECT = re.compile(r"\b(?:a que se refiere|que se entiende|a que alude|como describ\w*|que significa)\b")
GENERIC_INDIRECT = re.compile(r"\b(?:habla|hablan|alude|aluden) de(?:l)? (?:la |el )?([a-z ]{3,64})$")
DOC_SPLIT = re.compile(r"\s+y\s+(?=(?:explica|describe|define|enumera)\b)", re.I)
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


@dataclass(frozen=True)
class DocumentNeed:
    topic: str
    kind: str
    scope: str | None

    @property
    def keywords(self):
        return tuple(terms(self.topic))

    @property
    def permitted(self):
        return sorted(set(self.keywords) | set(TOPIC_ALIASES.get(normalize(self.topic), ())))


def document_needs(question):
    content = documentary_query(question)
    text = plain(content)
    if RESTRICTION.search(text) or re.search(r"\d", text):
        return []
    # Para el rescate se reconocen ámbitos que el motor puede comprobar. Una
    # mención a otra clase de informe o a otra entidad queda en el flujo local.
    scope = next((scope for scope in ("tenedora", "gfnorte", "banorte")
                  if re.search(rf"\b{scope}\b", text)), None)
    if scope is None and re.search(r"\b(?:informe|documento) ficticio\b", text):
        scope = "ficticio"
    if re.search(r"\b(?:banco|grupo|filial|subsidiaria|anexo)\b", text):
        return []
    if re.search(r"\b(?:en|segun) (?:los |el )?(?:informes?|reportes?|documentos?)\b", text):
        if not scope and not re.search(r"\b(?:disponibles|ficticio)\b", text):
            return []
    parts = DOC_SPLIT.split(content)
    if len(parts) > 2:
        return []
    needs = []
    for part in parts:
        cleaned = plain(part).strip(" ¿?!.,")
        cleaned = re.sub(r"\b(?:en |de )?(?:los )?(?:informes?|reportes?|documentos?) de (?:la )?"
                         r"(?:tenedora|gfnorte|banorte)\b", "", cleaned).strip()
        cleaned = re.sub(r"\b(?:de|para) (?:la )?(?:tenedora|gfnorte|banorte)\b", "", cleaned).strip()
        cleaned = re.sub(r"^(?:explica|describe|define|enumera) (?:aparte |por separado )?", "", cleaned).strip()
        topic = definition_topic(cleaned)
        if topic:
            kind = "definition"
        elif INDIRECT.search(cleaned):
            candidates = [topic for topic, aliases in TOPIC_ALIASES.items()
                          if set(topic.split()) <= set(terms(cleaned)) or ("ccl" in aliases and "ccl" in terms(cleaned))]
            match = GENERIC_INDIRECT.search(cleaned)
            topic = candidates[0] if len(candidates) == 1 else match[1] if match else ""
            topic = CONCEPT_SYNONYMS.get(normalize(topic), topic)
            kind = "definition"
        elif len(parts) == 2:
            if cleaned.startswith("como usa"):
                cleaned = cleaned.removeprefix("como usa ")
            topic = cleaned
            if normalize(topic) == "ccl":
                topic = "coeficiente de cobertura de liquidez"
            kind = "list" if normalize(topic).startswith("objetivos ") else (
                "definition" if normalize(topic) in TOPIC_ALIASES else "passage"
            )
        else:
            return []
        words = terms(topic)
        if not 2 <= len(words) <= 8:
            return []
        needs.append(DocumentNeed(CANONICAL_TOPICS.get(normalize(topic), topic), kind, scope))
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
    if UNSAFE_PASSAGE.search(text) or not wanted <= set(terms(snippet)):
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
    if need.kind == "list":
        return "•" in snippet
    return "." in snippet and ":" not in snippet.partition(".")[0]


def report_scope(need, title):
    if not need.scope:
        return True
    name = set(terms(title))
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


def verified_passage(corpus, ref, need):
    name, data = corpus.original(ref.doc_id)
    if not report_scope(need, name):
        return None
    with PDF_LOCK, pymupdf.open(stream=data, filetype="pdf") as pdf:
        page = pdf[ref.pdf_page - 1]
        snippet = ""
        if need.kind == "list":
            snippet = list_under_heading(page, set(need.keywords))
        elif need.kind == "definition":
            snippet = definition_under_heading(page, need.topic) or ""
            if not snippet:
                snippet = definition_on_page(page, need)
        if not snippet and need.kind != "list":
            # Un bloque puede contener varias oraciones. La evidencia devuelta
            # es solo la oración que demuestra el apartado.
            for block in page.get_text("blocks"):
                if block[6] != 0:
                    continue
                for sentence in re.split(r"(?<=[.!?])\s+", " ".join(block[4].split())):
                    if doc_support(need, sentence) and sentence.endswith((".", "?", "!")):
                        snippet = sentence
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
        allowed = {entry["slot"]: set(entry["terms"]) for entry in slots}
        chosen = {}
        for step in plan.subquestions:
            chosen_terms = {normalize(item) for item in step.search_terms}
            if (step.slot not in allowed or step.slot in chosen
                    or not chosen_terms <= allowed[step.slot] or len(chosen_terms) != len(step.search_terms)):
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
        if base.status == "abstained":
            if primary.operation != "participation" and not comparable_periods(primary):
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
            return base, "protected"
        secondary = financial_need(question, primary)
        if secondary is None or "financial_calculator" not in base.tools_used or not base.citations:
            return base, "complete"
        pending = self.partial(base, secondary.metric)
        try:
            chosen, stage = await self.ask(question, [{"slot": 0, "tipo": "cálculo", "terms": []}], totals, budget)
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
        return base.model_copy(update={
            "answer": f"{base.answer} {result.answer}", "citations": citations,
            "warnings": list(dict.fromkeys([*base.warnings, *result.warnings])),
        }), "rescued"

    async def documents(self, question, base, budget, totals):
        needs = document_needs(question)
        if not needs:
            return base, "protected" if base.status == "abstained" else "complete"
        if len(needs) == 1 and base.status == "answered":
            return base, "complete"
        covered = {i: cite for i, need in enumerate(needs) for cite in base.citations
                   if report_scope(need, cite.filename) and doc_support(need, cite.snippet)}
        slots = [{"slot": i, "tipo": need.kind, "tema": need.topic, "terms": need.permitted}
                 for i, need in enumerate(needs) if i not in covered]
        if not slots:
            return base, "complete"
        initial = set(covered)
        pending = self.partial(base, " y ".join(needs[slot["slot"]].topic for slot in slots)) if len(needs) > 1 else base
        stage = "fallback"
        try:
            chosen, stage = await self.ask(question, slots, totals, budget)
            if not chosen:
                return pending, stage
            catalog = None
            for i, search_terms in chosen.items():
                need = needs[i]
                documents = None
                if need.scope:
                    if catalog is None:
                        catalog = await budget.call("list_documents", self.corpus.catalog)
                    documents = {doc["doc_id"] for doc in catalog if report_scope(need, doc["filename"])}
                expanded = set(search_terms) - set(need.keywords)
                query = " ".join(dict.fromkeys([*need.keywords, *search_terms]))
                if need.kind == "definition" and not expanded:
                    query = f"¿Cómo se define el {need.topic}?"
                refs = await budget.call("search_corpus", self.corpus.search_corpus,
                                         SearchRequest(query=query, documents=documents, top_k=8))
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
        parts = [cite.snippet for cite in citations]
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
