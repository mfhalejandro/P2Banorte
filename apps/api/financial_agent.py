"""Orquestación local de herramientas V3 y construcción de la respuesta auditada."""
import asyncio
import re
from dataclasses import dataclass, field
from decimal import Decimal, localcontext
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .agent import ChatResponse, ProviderUnavailable
from .corpus import Citation, Corpus, SourceRef, documentary_query
from .finance import Abstain, Operand, Operation, PERIOD, Period, calculate, check_stock_sum, display, local_period, normalize
from .financial_evidence import CURRENCY, UnverifiedBasis, currency_key, find_candidates, read_operand

ToolName = Literal["list_documents", "search_corpus", "read_source", "financial_calculator", "inspect_page_visual"]


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: ToolName
    arguments: dict


class ToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ListArgs(ToolArgs):
    offset: int = Field(default=0, ge=0, le=10_000)
    limit: int = Field(default=10, ge=1, le=20)


class PeriodArgs(ToolArgs):
    period: str


class ReadArgs(PeriodArgs):
    ref: SourceRef
    parse_tables: Literal[True] = True


class CalcArgs(ToolArgs):
    operation: Operation
    base: str
    current: str


class InspectArgs(ToolArgs):
    source_id: str


@dataclass(frozen=True)
class Intent:
    metric: str
    entity: str | None
    base: Period
    current: Period
    operation: Operation
    inspect: bool
    output_currency: str | None = None
    output_scale: str | None = None
    percentage_points: bool = False


FINANCIAL_VERB = r"(?:compara(?:r)?|calcula(?:r)?|suma(?:r)?(?!\s+(?:de|en|entre)\b))"
CHANGE_VERB = r"(?:cambi[oó]|vari[oó]|aument[oó]|disminuy[oó]|subi[oó]|baj[oó]|creci[oó]|cay[oó]|se\s+(?:increment[oó]|redujo))"
OPERATION_NOUN = r"(?:variaci[oó]n(?:\s+porcentual)?|diferencia|cambio|comparaci[oó]n|suma|raz[oó]n|ratio)"
NOMINAL_OPERATION = rf"(?:la\s+|el\s+)?(?P<operation>{OPERATION_NOUN})\s+(?:del?|en|entre)\b"
FINANCIAL_REQUEST = re.compile(
    rf"(?:^|(?<=[.!?;,])\s+|(?=¿))[¿¡\s]*(?:"
    rf"(?P<relative>en\s+qu[eé]\s+porcentaje\s+{CHANGE_VERB})\b|"
    rf"(?P<change>(?:c[oó]mo|(?:en\s+)?cu[aá]nto)\s+{CHANGE_VERB})\b|"
    rf"(?P<verb>{FINANCIAL_VERB})\b|"
    rf"(?:cu[aá]l\s+(?:fue|es)\s+)?{NOMINAL_OPERATION})",
    re.I,
)
POINTS = re.compile(r"\ben\s+puntos\s+porcentuales\b", re.I)
VALUE_FORMAT = re.compile(r"(?:muestra|indica|incluye)\s+(?:ambos\s+valores|los\s+valores\s+(?:utilizados|originales))", re.I)
QUALITATIVE_SUBJECT = re.compile(
    r"^(?:(?:las?|el|los)\s+)?(?:pol[ií]ticas?|procedimientos?|estrategias?|lineamientos?|metodolog[ií]as?)\b",
    re.I,
)
SUBJECT_CONTEXT = re.compile(r"^(?:para|sobre|respecto\s+(?:de|a))\s+(.+?)[,;\s]*$", re.I)


@dataclass(frozen=True)
class FinancialRequest:
    content: str
    indicator: str
    operation: Operation
    percentage_points: bool


def recognize_financial_request(question: str) -> FinancialRequest | None:
    content = documentary_query(question)
    content = " ".join(
        part for part in re.split(r"(?<=[.?!])\s+", content)
        if not VALUE_FORMAT.fullmatch(part.strip(" ¿¡?!."))
    )
    cue = FINANCIAL_REQUEST.search(content)
    if not cue:
        return None
    first_clause = content[:cue.start()].strip(" ¿¡")
    context = SUBJECT_CONTEXT.fullmatch(first_clause)
    after_cue = content[cue.end():].strip()
    operation_word = cue["operation"] or cue["verb"] or ""
    nominal = re.match(NOMINAL_OPERATION, after_cue, re.I) if cue["verb"] else None
    if nominal:
        operation_word = nominal["operation"]
        after_cue = after_cue[nominal.end():].strip()
    clause = re.split(r"(?<=[.!?])\s+", after_cue, maxsplit=1)[0]
    indicator = context[1] if context else PERIOD.split(clause, maxsplit=1)[0]
    if cue["change"] and QUALITATIVE_SUBJECT.match(indicator):
        return None
    points = POINTS.search(content) is not None
    operation: Operation = "difference"
    keyword = normalize(operation_word)
    if keyword.startswith("suma"):
        operation = "sum"
    elif keyword in {"razon", "ratio"}:
        operation = "ratio"
    elif cue["relative"] or (keyword.startswith("variacion") and not points):
        operation = "percent_change"
    return FinancialRequest(content, indicator, operation, points)


def requires_financial_tools(question: str) -> bool:
    """Una solicitud de operación puede reconocerse antes de validar sus operandos."""
    return recognize_financial_request(question) is not None


def parse_intent(question: str) -> Intent:
    missing = "Indica un indicador y dos periodos distintos, por ejemplo «Compara utilidad neta de Grupo Faro entre 3T24 y 3T25»."
    request = recognize_financial_request(question)
    if request is None:
        raise Abstain(missing)
    matches = list(PERIOD.finditer(request.content))
    periods = list(dict.fromkeys(local_period(match) for match in matches))
    prefix = request.indicator.strip(" ¿?!:,")
    prefix = re.sub(r"^(?:la|el|los|las)\s+", "", prefix, flags=re.I)
    metric_entity = re.sub(r"\s+(?:entre|del|de|en|para)\s*$", "", prefix, flags=re.I).strip()
    unit_pattern = re.compile(
        rf"\s+(?:expresad[oa]s?\s+)?en\s+{CURRENCY.pattern}(?=$|\s+de\s+(?:grupo|banco|gfnorte)\b)", re.I,
    )
    inline_units = [match.groups() for match in unit_pattern.finditer(metric_entity)]
    metric_entity = unit_pattern.sub("", metric_entity)
    subject = re.search(r"\s+de\s+((?:grupo|banco|gfnorte)\b.*)$", metric_entity, re.I)
    metric, entity = (metric_entity[:subject.start()], subject[1]) if subject else (metric_entity, "")
    if len(periods) != 2 or not normalize(metric):
        raise Abstain(missing)
    key = request.content.casefold()
    if "acumulad" in key and all(p.kind == "quarter" for p in periods):
        raise Abstain("Indica el periodo acumulado explícitamente, por ejemplo 9M25.")
    if request.percentage_points and request.operation != "difference":
        raise Abstain("La unidad solicitada exige una diferencia entre tasas, con dos tasas comparables.")
    ending = request.content[matches[-1].end():]
    units = [match.groups() for match in re.finditer(rf"\ben\s+{CURRENCY.pattern}", ending, re.I)]
    units.extend(inline_units)
    currencies = {currency_key(name) for _, name in units}
    scales = {scale.lower() for scale, _ in units if scale}
    if len(currencies) > 1 or len(scales) > 1 or (request.percentage_points and units):
        raise Abstain("La consulta especifica unidades o monedas incompatibles.")
    return Intent(metric, entity or None, *periods, request.operation, "inspecciona" in key,
                  next(iter(currencies), None), next(iter(scales), None), request.percentage_points)


@dataclass
class Trace:
    tools: list[str] = field(default_factory=list)
    documents: list[dict] = field(default_factory=list)
    searched: dict[str, list[SourceRef]] = field(default_factory=dict)
    attempted: dict[str, set[tuple[str, int]]] = field(default_factory=dict)
    observed: dict[str, Operand] = field(default_factory=dict)
    rejected: dict[str, str] = field(default_factory=dict)
    basis_warnings: dict[str, tuple[str, Citation | None]] = field(default_factory=dict)
    result: tuple[Operand, Operand, tuple[Decimal, str, str]] | None = None
    inspected: bool = False


class LocalToolDouble:
    """Proveedor determinista, sin acceso a red, usado también en la demo."""

    mode = "financiero local (doble)"

    async def propose(self, intent, trace):
        if not trace.tools:
            return ToolCall(name="list_documents", arguments={})
        periods = (intent.base, intent.current)
        for period in periods:
            if period.label not in trace.searched:
                return ToolCall(name="search_corpus", arguments={"period": period.label})
        for period in periods:
            label = period.label
            attempted = trace.attempted.get(label, set())
            for ref in trace.searched[label]:
                found = any(item.period == period for item in trace.observed.values())
                if len(attempted) >= (3 if found or intent.inspect else 4):
                    break
                if (ref.doc_id, ref.pdf_page) not in attempted:
                    return ToolCall(name="read_source", arguments={"period": label, "ref": ref.model_dump()})
        missing = [p.label for p in periods if not any(item.period == p for item in trace.observed.values())]
        if missing:
            reasons = [f"{label}: "
                       f"{trace.basis_warnings.get(label, (trace.rejected.get(label, 'no se encontró evidencia'), None))[0]}"
                       for label in missing]
            raise Abstain(". ".join(reason.rstrip(".") for reason in reasons) + ".")
        base, current = self.choose_pair(intent, trace.observed)
        if intent.inspect and not trace.inspected:
            return ToolCall(name="inspect_page_visual", arguments={"source_id": current})
        if trace.result is None:
            return ToolCall(name="financial_calculator", arguments={
                "operation": intent.operation, "base": base, "current": current,
            })
        return None

    @classmethod
    def choose_pair(cls, intent, observed):
        base = cls.choose(intent.base, observed)
        current = cls.choose(intent.current, observed)
        # Una moneda sin código se comparte únicamente dentro de su propia tabla.
        # Elegir esa pareja si las cifras de las demás lecturas coinciden.
        for base_id, first in observed.items():
            for current_id, second in observed.items():
                if (first.period == intent.base and second.period == intent.current
                        and first.unit.currency == second.unit.currency):
                    return base_id, current_id
        return base, current

    @staticmethod
    def choose(period, observed):
        candidates = [(key, value) for key, value in observed.items() if value.period == period]
        with localcontext() as context:
            context.prec = 50
            signatures = {(normalize(p.entity), p.unit.name, (p.unit.currency or "").split(":", 1)[0],
                           p.value * p.unit.scale,
                           normalize(p.basis), p.note, p.comparable_basis, p.definition) for _, p in candidates}
        if len(signatures) != 1:
            raise Abstain(f"{period.label}: las fuentes disponibles muestran cifras o bases incompatibles.")
        return candidates[0][0]


class FinancialAgent:
    def __init__(self, corpus: Corpus, provider=None, max_calls=12, timeout=15):
        self.corpus = corpus
        self.provider = provider or LocalToolDouble()
        self.max_calls = max_calls
        self.timeout = timeout

    async def answer(self, question):
        trace = Trace()
        try:
            intent = parse_intent(question)
            check_stock_sum(intent.operation, intent.metric)
            async with asyncio.timeout(self.timeout):
                while True:
                    proposal = await self.provider.propose(intent, trace)
                    if proposal is None:
                        if trace.result is None:
                            raise Abstain("La comparación no tiene un resultado respaldado por la calculadora.")
                        break
                    if len(trace.tools) >= self.max_calls:
                        raise ProviderUnavailable("Se alcanzó el límite de herramientas.")
                    call = ToolCall.model_validate(proposal)
                    trace.tools.append(call.name)
                    await asyncio.to_thread(self.execute, intent, trace, call)
        except ValidationError as exc:
            raise ProviderUnavailable("La llamada de herramienta es inválida.") from exc
        except Abstain as exc:
            return self.response(trace, str(exc))
        return self.response(trace)

    def execute(self, intent, trace, call):
        name, args = call.name, call.arguments
        periods = {p.label: p for p in (intent.base, intent.current)}
        if name == "list_documents":
            params = ListArgs.model_validate(args)
            trace.documents = self.corpus.catalog()[params.offset:params.offset + params.limit]
        elif name == "search_corpus":
            params = PeriodArgs.model_validate(args)
            period = periods.get(params.period)
            if period is None:
                raise Abstain("La búsqueda propone un periodo ajeno a la pregunta.")
            other = intent.current if period == intent.base else intent.base
            trace.searched[params.period] = find_candidates(self.corpus, intent.metric, period, other)
        elif name == "read_source":
            params = ReadArgs.model_validate(args)
            if params.ref not in trace.searched.get(params.period, []):
                raise Abstain("La referencia no procede de la búsqueda de este periodo.")
            attempted = trace.attempted.setdefault(params.period, set())
            attempted.add((params.ref.doc_id, params.ref.pdf_page))
            try:
                period = periods[params.period]
                other = intent.current if period == intent.base else intent.base
                operand = read_operand(self.corpus, params.ref, intent.metric, period, other=other,
                                       requested_currency=intent.output_currency, requested_scale=intent.output_scale)
                if intent.entity and normalize(intent.entity) != normalize(operand.entity):
                    raise Abstain("La entidad de la fuente difiere de la solicitada.")
            except (RuntimeError, OSError):
                trace.rejected[params.period] = "No se pudo leer la página original."
            except UnverifiedBasis as exc:
                if intent.entity and normalize(intent.entity) != normalize(exc.entity):
                    trace.rejected[params.period] = "La entidad de la fuente difiere de la solicitada."
                else:
                    trace.basis_warnings.setdefault(params.period, (str(exc), exc.citation))
            except Abstain as exc:
                trace.rejected[params.period] = str(exc)
            else:
                trace.observed[operand.citation.evidence_id] = operand
        elif name == "inspect_page_visual":
            params = InspectArgs.model_validate(args)
            cited = trace.observed.get(params.source_id)
            if cited is None:
                raise Abstain("La inspección visual necesita una página leída en esta consulta.")
            self.corpus.render(cited.citation.doc_id, cited.citation.pdf_page, 125)
            trace.inspected = True
        elif name == "financial_calculator":
            params = CalcArgs.model_validate(args)
            base = trace.observed.get(params.base)
            current = trace.observed.get(params.current)
            if (not base or not current or params.operation != intent.operation
                    or base.period != intent.base or current.period != intent.current):
                raise Abstain("La calculadora requiere ambos operandos verificados para la operación solicitada.")
            if intent.output_currency:
                actual = (current.unit.currency or "").split(":", 1)[0]
                if actual != intent.output_currency:
                    raise Abstain("La evidencia no acredita la moneda solicitada. Indica una moneda respaldada por los originales.")
                if intent.output_scale and not current.unit.label.lower().startswith(intent.output_scale):
                    raise Abstain("El cálculo está respaldado en otra escala. Consulta en la escala indicada en las fuentes.")
            if intent.percentage_points and any(item.unit.label != "%" for item in (base, current)):
                raise Abstain("La unidad solicitada exige una diferencia entre tasas, con dos tasas comparables.")
            trace.result = base, current, calculate(params.operation, base, current)

    @staticmethod
    def operand_text(operand):
        if operand.unit.label == "%" and "%" in operand.original:
            return operand.original
        return f"{operand.original} {operand.unit.label}"

    def response(self, trace, reason=None):
        warnings = []
        citations = {}
        if reason:
            answer = f"No puedo calcular la comparación. {reason}"
            per_period = {item.period for item in trace.observed.values()}
            for period in sorted(per_period, key=lambda item: (item.year, item.end, item.kind)):
                try:
                    source = LocalToolDouble.choose(period, trace.observed)
                except Abstain:
                    continue
                item = trace.observed[source]
                answer += f" {period.label}: {self.operand_text(item)} ({item.entity})."
                citations[item.citation.evidence_id] = item.citation
            established = {period.label for period in per_period}
            for label, (warning, citation) in trace.basis_warnings.items():
                if label not in established:
                    warnings.append(warning)
                    if citation:
                        citations[citation.evidence_id] = citation
            for item in trace.observed.values():
                if item.note and item.note_citation:
                    warnings.append(item.note)
                    citations[item.note_citation.evidence_id] = item.note_citation
            if warnings and "cambio de perímetro" not in reason:
                answer += " " + warnings[0]
        else:
            base, current, (value, unit, formula) = trace.result
            conversion = ""
            if base.unit.scale != current.unit.scale:
                with localcontext() as context:
                    context.prec = 50
                    normalized = base.value * base.unit.scale / current.unit.scale
                conversion = f" B equivale a {normalized:f} {current.unit.label}."
            answer = (f"{current.metric} · {current.entity}. "
                      f"Base B ({base.period.label}): {self.operand_text(base)}."
                      f"{conversion} Periodo A ({current.period.label}): {self.operand_text(current)}. "
                      f"{formula} = {display(value)} {unit}.")
            for item in (base, current):
                citations[item.citation.evidence_id] = item.citation
                if item.note:
                    warnings.append(item.note)
                    if item.note_citation:
                        citations[item.note_citation.evidence_id] = item.note_citation
            if warnings:
                answer += " " + warnings[0]
        return ChatResponse(answer=answer, citations=list(citations.values()), warnings=list(dict.fromkeys(warnings)),
                            tools_used=trace.tools, request_id=uuid4().hex, provider_mode=self.provider.mode,
                            status="abstained" if reason else "answered")
