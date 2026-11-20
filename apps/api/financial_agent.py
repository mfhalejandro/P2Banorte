"""Orquestación local de herramientas V3 y construcción de la respuesta auditada."""
import asyncio
import re
from dataclasses import dataclass, field, replace
from decimal import Decimal, localcontext
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .agent import ChatResponse, ProviderUnavailable
from .corpus import Citation, Corpus, SourceRef, documentary_query
from .finance import Abstain, Operand, Operation, PERIOD, Period, calculate, check_periods, check_stock_sum, display, local_period, normalize
from .currency_request import verify_currency_request
from .financial_evidence import CURRENCY, TableCache, UnverifiedBasis, currency_key, find_candidates, read_operand
from .market_table import is_market_metric

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
    additional_difference: bool = False
    currencies: tuple[str, ...] = ()
    definition_check: bool = False
    consolidated: bool = False


FINANCIAL_VERB = r"(?:compara(?:r)?|calcula(?:r)?|suma(?:r)?(?!\s+(?:de|en|entre)\b))"
CHANGE_VERB = r"(?:cambi[oó]|vari[oó]|aument[oó]|disminuy[oó]|subi[oó]|baj[oó]|creci[oó]|cay[oó]|mejor[oó]|empeor[oó]|se\s+(?:increment[oó]|redujo|movi[oó]))"
OPERATION_NOUN = r"(?:variaci[oó]n(?:\s+porcentual)?|diferencia(?:\s+absoluta)?|cambio|comparaci[oó]n|suma|raz[oó]n|ratio)"
NOMINAL_OPERATION = rf"(?:la\s+|el\s+)?(?P<operation>{OPERATION_NOUN})\s+(?:del?|en|entre)\b"
NOMINAL_PROMPT = rf"(?:dame|muestra|indica|estima|determina|reporta)(?=\s+(?:(?:la|el)\s+)?{OPERATION_NOUN}\s+(?:del?|en|entre)\b)"
FINANCIAL_REQUEST = re.compile(
    rf"(?:^|(?<=[.!?;,])\s+|(?=¿))[¿¡\s]*(?:"
    rf"(?P<relative>en\s+qu[eé]\s+porcentaje\s+{CHANGE_VERB})\b|"
    rf"(?P<change>(?:c[oó]mo|(?:en\s+)?cu[aá]nto)\s+{CHANGE_VERB})\b|"
    rf"(?P<verb>{FINANCIAL_VERB}|{NOMINAL_PROMPT})\b|"
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
    additional_difference: bool = False
    definition_check: bool = False


ORDINAL = {"primer": 1, "primero": 1, "segundo": 2, "tercer": 3, "tercero": 3, "cuarto": 4}
QUARTER = r"(?:primer(?:o)?|segundo|tercer(?:o)?|cuarto)"
MONTH_END = {"marzo": 3, "junio": 6, "septiembre": 9, "diciembre": 12}
WRITTEN_PERIOD = re.compile(
    rf"\b(?:(?P<quarter>{QUARTER})\s+trimestres?|"
    r"primeros\s+(?P<months>tres|seis|nueve|doce)\s+meses|"
    r"(?:acumulad[oa]\s+(?:a|al|hasta)|enero\s*(?:[-–—]|a)\s*)\s*"
    r"(?P<cutoff>marzo|junio|septiembre|diciembre))"
    r"(?:\s+de(?:l\s+año)?\s+(?P<year>20\d{2})|\s+de\s+(?:ese|dicho)(?:\s+mismo)?\s+año)?", re.I,
)
COMPARABILITY_QUERY = re.compile(
    r"^(?:se puede afirmar que\s+)?(.+?)\s+(?:tuvo|experiment[oó]|registr[oó])"
    r"\s+una\s+variaci[oó]n\s+(?:directamente\s+)?comparable\s+entre\b", re.I,
)
SHARE_QUERY = re.compile(r"\bqu[eé]\s+(?:porcentaje|proporci[oó]n|fracci[oó]n porcentual)\s+representa\s+([^?]+)", re.I)
DUAL_CHANGE = re.compile(
    r"\b(?:calcula|determina|indica)\s+(?:la\s+)?diferencia\s+(?:absoluta\s+)?y\s+(?:la\s+)?"
    r"variaci[oó]n\s+(?:relativa|porcentual)\s+(?:del?|en)\b", re.I,
)
BOUND_DUAL = re.compile(
    r"^para (?P<subject>[^,;]+),\s*(?:calcula|muestra|indica|dame)\s+"
    r"(?:la )?diferencia absoluta y (?:la )?variaci[oó]n (?:relativa|porcentual)\b", re.I
)
NOMINAL_RATE = re.compile(
    r"\b(?:retroceso|ca[ií]da|crecimiento|incremento|descenso|variaci[oó]n) porcentual "
    r"(?:del?|de)\s+(?P<subject>[^?]+)", re.I
)
RELATIVE_QUERY = re.compile(rf"\b(?:determina\s+)?cu[aá]nto\s+{CHANGE_VERB}\s+porcentualmente\b", re.I)
TWO_CURRENCIES = re.compile(
    rf"\b(?:tanto\s+)?en\s+({CURRENCY.pattern})\s+(?:como|y)\s+(?:en\s+)?({CURRENCY.pattern})", re.I,
)

METRIC = re.compile(
    r"\b(?P<profit>utilidad neta)|\b(?P<roa>ROA|rendimiento sobre (?:los? )?activos)|"
    r"\b(?P<roe>ROE|rendimiento sobre (?:el )?capital(?: contable)?)|"
    r"\b(?P<market>capitalizaci[oó]n (?:de mercado|burs[aá]til))|"
    r"\b(?P<assets>activos? totales?|activo total|total de activos)|"
    r"\b(?P<equity>capital contable)\b", re.I,
)
METRIC_NAMES = {"profit": "utilidad neta", "roa": "ROA", "roe": "ROE", "market": "capitalización de mercado",
                "assets": "activo total", "equity": "capital contable"}
ENTITY_BOUNDARY = (
    r"(?=[,.;?!:]|\s*$|\s+(?:entre|respecto|en|para|del?|al|desde|hasta|durante|seg[uú]n|"
    r"si|cuando|suponiendo|considerando|expresad[oa]s?|[uú]nicamente|exclusivamente)\b|"
    rf"\s+{PERIOD.pattern})"
)
ENTITY_NAME = re.compile(
    rf"\b(?P<known>GFNorte|Grupo Financiero Banorte)\b{ENTITY_BOUNDARY}|"
    rf"\b(?:del?|para|sobre)(?:\s+la\s+entidad)?\s+"
    rf"(?P<other>(?:Banco|Grupo|GFNorte|Empresa|Sociedad|Compa[ñn][ií]a)\b[^,.;?!:]*?){ENTITY_BOUNDARY}",
    re.I,
)
TEMPORAL_SHARE = re.compile(
    r"\b(?:qu[eé] (?:porcentaje|parte|proporci[oó]n|fracci[oó]n)(?: porcentual)?\b.{0,150}"
    r"\b(?:corresponde|pertenece|aporta|dentro)|(?:forma parte|participaci[oó]n)\b.{0,100}\bacumulad|"
    r"acumulad\w*\b.{0,130}\bparticipaci[oó]n)\b", re.I,
)
CHANGE_QUESTION = re.compile(
    rf"\b(?:{CHANGE_VERB}|avanz[oó]|perdi[oó]|evolucion\w*|cu[aá]ntos?.{{0,55}}adicionales|"
    r"variaci[oó]n absoluta|diferencia absoluta|magnitud.{0,30}(?:incremento|descenso)|crecimiento directo|"
    r"(?:crecimiento|variaci[oó]n) (?:relativ[oa]|porcentual)|cambio|movimiento)\b", re.I,
)
RELATIVE_UNIT = re.compile(r"\b(?:porcentualmente|porcentual|relativ[oa]|qu[eé] porcentaje|crecimiento directo)\b", re.I)
EXPLICIT_POINTS = re.compile(r"\bpuntos porcentuales\b", re.I)
PURPOSE = re.compile(r"^para\s+(?:obtener|estimar|conseguir|construir|expresar)\b", re.I)
UNSUPPORTED_QUALIFIER = re.compile(
    r"\b(?:solo|solamente|[uú]nicamente|exclusiv\w*|sin|excepto|ajustad\w*|reexpresad\w*|"
    r"individual|no consolidad\w*)\b", re.I,
)
REPRESENTED_QUALIFIER = re.compile(
    rf"\b(?:(?:solo|solamente|[uú]nicamente|exclusivamente)\s+(?:(?:en|al|la|el)\s+)?"
    rf"(?={CURRENCY.pattern}|{METRIC.pattern}|[1-4]T\d\d\b)"
    r"|sin\s+(?:mezclar\s+(?:los\s+)?valores|cruzar\s+periodos)|(?:y\s+)?no\s+sumes\s+los\s+saldos)\b",
    re.I,
)


def normalize_periods(text: str) -> str:
    text = re.sub(
        rf"\b({QUARTER})(\s+(?:y|a|al)\s+(?:el\s+)?{QUARTER}\s+trimestres?\b)",
        r"\1 trimestre\2", text, flags=re.I,
    )
    year = None
    anchors = {local_period(hit).year for hit in PERIOD.finditer(text)}
    if len(anchors) == 1:
        year = str(next(iter(anchors)))

    written = list(WRITTEN_PERIOD.finditer(text))

    def replace_period(match):
        nonlocal year
        ordinal, months, cutoff, explicit = match.groups()
        if re.match(r" del año (?:siguiente|mismo)\b", text[match.end():], re.I):
            return match[0]
        year = explicit or year
        if not year and ordinal:
            following = next((hit for hit in written if hit.start() > match.end()), None)
            if following and re.fullmatch(r"\s+(?:y|a|al)\s+(?:el\s+)?", text[match.end():following.start()], re.I):
                year = following["year"]
        if not year:
            return match[0]
        size = MONTH_END[cutoff.lower()] if cutoff else {"tres": 3, "seis": 6, "nueve": 9, "doce": 12}.get((months or "").lower())
        label = f"{ORDINAL[ordinal.lower()]}T" if ordinal else f"{size}M"
        return label + year[-2:]

    def resolve_relative(match):
        ordinal, direction = match.groups()
        previous = list(PERIOD.finditer(normalized[:match.start()]))
        if not previous:
            return match[0]
        year = local_period(previous[-1]).year + int(direction == "siguiente")
        return f"{ORDINAL[ordinal.lower()]}T{year % 100:02}"

    normalized = WRITTEN_PERIOD.sub(replace_period, text)
    return re.sub(r"\b(primer(?:o)?|segundo|tercer(?:o)?|cuarto)(?: trimestre)? "
                  r"(?:de ese mismo año|del año (siguiente|mismo))\b", resolve_relative, normalized, flags=re.I)


def operational_request(content):
    """Interpretar operaciones explícitas sobre indicadores conocidos sin usar su posición como intención."""
    found = list(METRIC.finditer(content))
    metrics = {match.lastgroup for match in found}
    if len(metrics) != 1:
        return None
    metric = METRIC_NAMES[found[0].lastgroup]
    subject = next(ENTITY_NAME.finditer(content), None)
    if subject:
        metric += " de " + ("GFNorte" if subject["known"] else subject["other"])
    share = bool(TEMPORAL_SHARE.search(content))
    points = bool(EXPLICIT_POINTS.search(content))
    if (re.search(r"\bsuma(?:r)?\s+(?:los?|las?)\b", content, re.I)
            or re.search(r"\bcu[aá]nto\b.{0,45}\bsuma\s+del?\b", content, re.I)):
        operation: Operation = "sum"
    elif share:
        operation = "participation"
    elif points or CHANGE_QUESTION.search(content) or (
        found[0].lastgroup in {"roe", "roa"} and re.search(r"\bvariaci[oó]n\b", content, re.I)
    ):
        if len(set(local_period(hit) for hit in PERIOD.finditer(content))) < 2:
            return None
        operation = "percent_change" if RELATIVE_UNIT.search(content) and not points else "difference"
    else:
        return None
    definition = points and bool(re.search(r"\b(?:definici[oó]n|metodolog[ií]a)\b", content, re.I))
    additional = operation == "percent_change" and bool(re.search(r"\badicionales\b", content, re.I))
    return FinancialRequest(content, metric, operation, points, additional, definition)


def recognize_financial_request(question: str) -> FinancialRequest | None:
    content = normalize_periods(documentary_query(question))
    content = " ".join(
        part for part in re.split(r"(?<=[.?!])\s+", content)
        if not VALUE_FORMAT.fullmatch(part.strip(" ¿?!."))
    )
    if dual := BOUND_DUAL.match(content.strip(" ¿¡")):
        return FinancialRequest(content, PERIOD.split(dual["subject"], maxsplit=1)[0], "percent_change", False, True)
    if not DUAL_CHANGE.search(content) and (rate := NOMINAL_RATE.search(content)):
        indicator = PERIOD.split(rate["subject"], maxsplit=1)[0]
        return FinancialRequest(content, indicator, "percent_change", False)
    if share := SHARE_QUERY.search(content):
        return FinancialRequest(content, PERIOD.split(share[1], maxsplit=1)[0], "participation", False)
    if comparable := COMPARABILITY_QUERY.match(content.strip(" ¿")):
        return FinancialRequest(content, comparable[1], "difference", False)
    relative = RELATIVE_QUERY.search(content) or DUAL_CHANGE.search(content)
    if relative:
        rest = content[relative.end():]
        return FinancialRequest(content, PERIOD.split(rest, maxsplit=1)[0], "percent_change", False, True)

    first_clause, separator, continuation = content.partition(",")
    if separator and PURPOSE.match(first_clause):
        content = continuation.strip()
    if re.match(r"^al\s+(?:contrastar|comparar)\s+(?![1-4]t\d\d\b)", content, re.I) and EXPLICIT_POINTS.search(content):
        subject = re.sub(r"^al\s+(?:contrastar|comparar)\s+", "", content, flags=re.I)
        return FinancialRequest(content, PERIOD.split(subject, maxsplit=1)[0], "difference", True,
                                definition_check=bool(re.search(r"\bdefinici[oó]n\b", content, re.I)))

    operational = operational_request(content)
    if operational and (operational.operation in {"participation", "sum"} or operational.percentage_points
                        or (METRIC.match(operational.indicator).lastgroup in {"roe", "roa"}
                            and not RELATIVE_UNIT.search(content))):
        return operational
    cue = FINANCIAL_REQUEST.search(content)
    if not cue:
        return operational
    first_clause = content[:cue.start()].strip(" ¿¡")
    context = SUBJECT_CONTEXT.fullmatch(first_clause)
    if context and PERIOD.search(context[1]):
        context = None
    after_cue = content[cue.end():].strip()
    operation_word = cue["operation"] or cue["verb"] or ""
    nominal = re.match(NOMINAL_OPERATION, after_cue, re.I) if cue["verb"] else None
    if nominal:
        operation_word = nominal["operation"]
        after_cue = after_cue[nominal.end():].strip()
    clause = re.split(r"(?<=[.!?])\s+", after_cue, maxsplit=1)[0]
    indicator = context[1] if context else PERIOD.split(clause, maxsplit=1)[0]
    if QUALITATIVE_SUBJECT.match(indicator) and (cue["change"] or nominal or cue["operation"]):
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
    if operational and (not normalize(indicator) or re.match(r"(?:el\s+)?aumento\s+de\b", indicator, re.I)):
        return operational
    return FinancialRequest(content, indicator, operation, points)


def requires_financial_tools(question: str) -> bool:
    """Una solicitud de operación puede reconocerse antes de validar sus operandos."""
    return recognize_financial_request(question) is not None


def parse_intent(question: str) -> Intent:
    verify_currency_request(question)
    question = re.sub(r"\b(?:exclusivamente|únicamente|unicamente|solamente|solo)\s+"
                      rf"(?={CURRENCY.pattern})", "", question, flags=re.I)
    missing = "Indica un indicador y dos periodos distintos para identificar la comparación solicitada."
    request = recognize_financial_request(question)
    if request is None:
        raise Abstain(missing)
    if request == operational_request(request.content) and UNSUPPORTED_QUALIFIER.search(
        REPRESENTED_QUALIFIER.sub("", request.content)
    ):
        # La paráfrasis no puede eliminar condiciones que el analizador no representa.
        raise Abstain("No se pudo interpretar la restricción indicada sin cambiar el alcance de la operación.")
    matches = list(PERIOD.finditer(request.content))
    periods = list(dict.fromkeys(local_period(match) for match in matches))
    prefix = request.indicator.strip(" ¿?!:,")
    prefix = re.sub(r"^(?:la|el|los|las)\s+", "", prefix, flags=re.I)
    metric_entity = re.sub(r"\s+(?:respecto\s+al?|al\s+cierre\s+de|entre|del|de|en|para|al)(?:\s+(?:el|la|los|las))?\s*$", "", prefix, flags=re.I).strip()
    metric_entity = re.sub(r"\s+trimestral(?=\s+de\s|$)", "", metric_entity, flags=re.I)
    unit_pattern = re.compile(
        rf"\s+(?:expresad[oa]s?\s+)?en\s+{CURRENCY.pattern}(?=$|\s+de\s+(?:grupo|banco|gfnorte)\b)", re.I,
    )
    inline_units = [match.groups() for match in unit_pattern.finditer(metric_entity)]
    metric_entity = unit_pattern.sub("", metric_entity)
    # La entidad ocupa un complemento delimitado. Una entidad desconocida
    # conserva todo su nombre hasta el siguiente conector sintáctico.
    subject = ENTITY_NAME.search(metric_entity)
    metric = metric_entity[:subject.start()] if subject else metric_entity
    metric = re.sub(r"\s+del?\s*$", "", metric, flags=re.I).strip()
    entities = [subject] if subject else list(ENTITY_NAME.finditer(request.content))
    entity = None
    if len(entities) == 1:
        entity = entities[0]["other"] or entities[0]["known"]
    elif entities:
        raise Abstain("No se pudo identificar una sola entidad para esta operación.")
    consolidated = False
    if consolidated_metric := re.fullmatch(r"(.+?)\s+consolidad[oa]s?", metric, flags=re.I):
        if METRIC.fullmatch(consolidated_metric[1]):
            metric = consolidated_metric[1]
            consolidated = True
    if metric_match := METRIC.fullmatch(metric.strip()):
        metric = METRIC_NAMES[metric_match.lastgroup]
    if entity and normalize(entity) == "grupo financiero banorte":
        entity = "GFNorte"
    if len(periods) != 2 or not normalize(metric):
        check_stock_sum(request.operation, metric)
        raise Abstain(missing)
    if (request.operation == "participation" and periods[0].kind != "ytd"
            or request.operation != "participation" and
            re.search(r"\brespecto\s+(?:al?|de)\s+$", request.content[:matches[-1].start()], re.I)):
        periods.reverse()
    key = request.content.casefold()
    if "acumulad" in key and all(p.kind == "quarter" for p in periods):
        raise Abstain("Indica el periodo acumulado explícitamente, por ejemplo 9M25.")
    if request.percentage_points and request.operation != "difference":
        raise Abstain("La unidad solicitada exige una diferencia entre tasas, con dos tasas comparables.")
    ending = request.content[matches[-1].end():]
    units = [match.groups() for match in re.finditer(rf"\ben\s+{CURRENCY.pattern}", ending, re.I)]
    dual = TWO_CURRENCIES.search(ending)
    currencies_requested = ()
    if dual:
        first_scale, first_name, second_scale, second_name = dual[2], dual[3], dual[5], dual[6]
        currencies_requested = tuple(dict.fromkeys(currency_key(name) for name in (first_name, second_name)))
        if len(currencies_requested) == 2 and not inline_units:
            units = [(scale, name) for scale, name in units if currency_key(name) not in currencies_requested]
            if first_scale or second_scale:
                if normalize(first_scale or "") != normalize(second_scale or ""):
                    raise Abstain("Las suboperaciones deben declarar la misma escala o ambas dejarla a la fuente.")
                units.append((first_scale, first_name))
    elif is_market_metric(metric) and re.search(r"\b(?:cada una de las dos|ambas) monedas (?:publicadas|reportadas)\b", key):
        # Las dos filas admitidas se verifican independientemente en el original.
        currencies_requested = ("MXN", "USD")
    units.extend(inline_units)
    # Una unidad anterior a los periodos o en una instrucción separada también obliga.
    if not currencies_requested:
        units.extend(match.groups() for match in re.finditer(
            rf"\b(?:en|usa|utiliza|moneda\s*:|cu[aá]ntos?)\s+{CURRENCY.pattern}", request.content, re.I))
    currencies = {currency_key(name) for _, name in units}
    scales = {scale.lower() for scale, _ in units if scale}
    if (len(currencies) > 1 or len(scales) > 1 or (request.percentage_points and units)
            or (currencies_requested and (inline_units or any(code not in currencies_requested for code in currencies)))):
        raise Abstain("La consulta especifica unidades o monedas incompatibles.")
    return Intent(metric, entity, *periods, request.operation, "inspecciona" in key,
                  next(iter(currencies), None), next(iter(scales), None), request.percentage_points,
                  request.additional_difference, currencies_requested, request.definition_check, consolidated)


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
    tables: TableCache = field(default_factory=dict)


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


class BudgetExhausted(ProviderUnavailable):
    pass


class FinancialAgent:
    def __init__(self, corpus: Corpus, provider=None, max_calls=12, timeout=15):
        self.corpus = corpus
        self.provider = provider or LocalToolDouble()
        self.max_calls = max_calls
        self.timeout = timeout

    async def answer(self, question, *, trace=None):
        try:
            intent = parse_intent(question)
            check_stock_sum(intent.operation, intent.metric)
        except Abstain as exc:
            return self.response(Trace(), str(exc))
        if not intent.currencies:
            return await self.run_intent(intent, trace)
        if intent.operation == "participation" or intent.percentage_points:
            return self.response(Trace(), "La operación solicitada no admite una salida en monedas.")

        results = []
        tables: TableCache = {}
        remaining = self.max_calls * 2
        deadline = asyncio.get_running_loop().time() + self.timeout
        for currency in intent.currencies:
            trace = Trace(tables=tables)
            try:
                async with asyncio.timeout_at(deadline):
                    reply = await self.run_intent(replace(intent, output_currency=currency), trace, remaining)
            except TimeoutError:
                reply = self.response(trace, "El plazo compartido no permitió verificar esta moneda.")
            except BudgetExhausted:
                reply = self.response(trace, "Se agotaron las llamadas compartidas antes de verificar esta moneda.")
            results.append((currency, reply))
            remaining -= len(trace.tools)
        first = results[0][1]
        return first.model_copy(update={
            "answer": " ".join(f"{code} — {reply.answer}" for code, reply in results),
            "tools_used": [tool for _, reply in results for tool in reply.tools_used],
            "citations": list({cite.evidence_id: cite for _, reply in results for cite in reply.citations}.values()),
            "warnings": list(dict.fromkeys(warning for _, reply in results for warning in reply.warnings)),
            "status": "answered" if any(reply.status == "answered" for _, reply in results) else "abstained",
        })

    async def run_intent(self, intent, trace=None, limit=None):
        trace = trace or Trace()
        limit = self.max_calls if limit is None else limit
        period_error = None
        try:
            check_periods(intent.operation, intent.base, intent.current)
        except Abstain as exc:
            period_error = str(exc)
            if intent.operation == "participation":
                return self.response(trace, period_error)
        try:
            check_stock_sum(intent.operation, intent.metric)
            async with asyncio.timeout(self.timeout):
                while True:
                    proposal = await self.provider.propose(intent, trace)
                    if proposal is None:
                        if trace.result is None:
                            raise Abstain("La comparación no tiene un resultado respaldado por la calculadora.")
                        break
                    if len(trace.tools) >= limit:
                        raise BudgetExhausted("Se alcanzó el límite de herramientas.")
                    call = ToolCall.model_validate(proposal)
                    if period_error and call.name == "financial_calculator":
                        raise Abstain(period_error)
                    trace.tools.append(call.name)
                    await asyncio.to_thread(self.execute, intent, trace, call)
        except ValidationError as exc:
            raise ProviderUnavailable("La llamada de herramienta es inválida.") from exc
        except Abstain as exc:
            return self.response(trace, period_error or str(exc))
        return self.response(trace, intent=intent)

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
                                       requested_currency=intent.output_currency, requested_scale=intent.output_scale,
                                       tables=trace.tables)
                if intent.entity and normalize(intent.entity) != normalize(operand.entity):
                    raise Abstain("La entidad de la fuente difiere de la solicitada.")
                if intent.consolidated and not re.match(r"consolidad[oa]\b", operand.basis, re.I):
                    raise Abstain("La fuente no acredita la base consolidada solicitada.")
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
                market_currency = actual in {"pesos", "dólares"} and base.basis == current.basis == "capitalización de la acción del grupo"
                alias = {"pesos": "MXN", "dólares": "USD"}.get(actual) if market_currency else None
                if actual != intent.output_currency and alias != intent.output_currency:
                    raise Abstain("La evidencia no acredita la moneda solicitada. Indica una moneda respaldada por los originales.")
                if intent.output_scale and not current.unit.label.lower().startswith(intent.output_scale):
                    raise Abstain("El cálculo está respaldado en otra escala. Consulta en la escala indicada en las fuentes.")
            if intent.percentage_points and any(item.unit.label != "%" for item in (base, current)):
                raise Abstain("La unidad solicitada exige una diferencia entre tasas, con dos tasas comparables.")
            if intent.definition_check and (not base.definition or not current.definition):
                raise Abstain("Las fuentes no acreditan las definiciones de ambos operandos.")
            trace.result = base, current, calculate(params.operation, base, current)

    @staticmethod
    def operand_text(operand):
        if operand.unit.label == "%" and "%" in operand.original:
            return operand.original
        return f"{operand.original} {operand.unit.label}"

    def response(self, trace, reason=None, *, intent=None):
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
            if intent and intent.additional_difference:
                delta, delta_unit, _ = calculate("difference", base, current)
                answer += f" Diferencia con signo: {display(delta)} {delta_unit}."
            if intent and intent.definition_check and base.definition and base.definition == current.definition:
                answer += " Las notas de ambas fuentes respaldan la misma definición del indicador."
            if intent and intent.operation == "participation":
                answer += " Es una participación del trimestre dentro del acumulado; los periodos no son equivalentes para medir crecimiento temporal."
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
