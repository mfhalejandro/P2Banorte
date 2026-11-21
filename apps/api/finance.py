"""Reglas de negocio para operandos comprobados en el PDF."""
import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from typing import Literal

from .corpus import Citation, terms

Operation = Literal["difference", "percent_change", "ratio", "participation", "sum"]
PERIOD = re.compile(r"(?<!\w)(?:([1-4])\s*T|([369])\s*M|(12)\s*M|(2)\s*S)\s*[- ]?\s*(20\d{2}|\d{2})(?!\w)", re.I)


class Abstain(ValueError):
    """Falta evidencia suficiente para producir un resultado financiero."""


@dataclass(frozen=True)
class Period:
    label: str
    kind: str
    months: int
    year: int
    end: int


def local_period(match):
    quarter, ytd, full, second_semester, digits = match.groups()
    year = int(digits) + (2000 if len(digits) == 2 else 0)
    if quarter:
        return Period(f"{quarter}T{year % 100:02}", "quarter", 3, year, int(quarter) * 3)
    if second_semester:
        return Period(f"2S{year % 100:02}", "semester", 6, year, 12)
    months = int(ytd or full)
    return Period(f"{months}M{year % 100:02}", "ytd", months, year, months)


@dataclass(frozen=True)
class Unit:
    name: str
    currency: str | None
    scale: Decimal
    label: str


@dataclass(frozen=True)
class Operand:
    citation: Citation
    metric: str
    entity: str
    period: Period
    unit: Unit
    basis: str
    original: str
    value: Decimal
    comparable_basis: str | None = None
    note: str | None = None
    note_citation: Citation | None = None
    additive: bool = False
    definition: str | None = None


def normalize(text):
    return " ".join(terms(text))


def decimal_from_source(original, *, comma_grouping=False):
    """Procesar una celda completa. Si un separador cambia la escala, exigir contexto."""
    value = re.sub(r"\s+", " ", original.strip().replace("−", "-")).removesuffix("%").strip()
    if value.startswith("(") and value.endswith(")"):
        value = "-" + value[1:-1].strip().removesuffix("%").strip()
    if re.fullmatch(r"[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?", value):
        if not comma_grouping and value.count(",") == 1 and "." not in value:
            raise Abstain("El separador numérico de la celda es ambiguo.")
        value = value.replace(",", "")
    elif re.fullmatch(r"[+-]?\d{1,3}(?:[. ]\d{3})+,\d+", value):
        value = value.replace(".", "").replace(" ", "").replace(",", ".")
    elif re.fullmatch(r"[+-]?\d{1,3}(?: \d{3})+(?:\.\d+)?", value):
        value = value.replace(" ", "")
    elif re.fullmatch(r"[+-]?\d+,\d{1,2}", value):
        value = value.replace(",", ".")
    if re.fullmatch(r"[+-]?\d{1,3}\.\d{3}", value) and not comma_grouping:
        raise Abstain("El separador numérico de la celda es ambiguo.")
    if not re.fullmatch(r"[+-]?\d{1,20}(?:\.\d{1,12})?", value):
        raise Abstain("La celda no contiene un decimal finito y legible.")
    return Decimal(value)


def check_stock_sum(operation: Operation, metric: str):
    name = normalize(metric.partition("(")[0])
    stocks = {"activo total", "activos totales", "total activo", "total activos", "pasivo total",
              "total pasivo", "capital contable", "saldo cierre", "capitalizacion mercado"}
    if operation == "sum" and name in stocks:
        raise Abstain("La magnitud de stock es un saldo a una fecha de corte y no es aditiva entre periodos. "
                      "Sumar dos saldos de cierre no produce un saldo anual.")


def check_periods(operation: Operation, base: Period, current: Period):
    if operation == "participation":
        if not (base.kind == "ytd" and current.kind == "quarter" and base.year == current.year
                and base.end - base.months <= current.end - current.months < current.end <= base.end):
            raise Abstain(f"El trimestre no está incluido en el acumulado solicitado ({current.label} frente a {base.label}).")
    elif (base.kind, base.months) != (current.kind, current.months):
        raise Abstain("Los periodos tienen distinto tipo o duración, por ejemplo trimestre frente a acumulado.")


def calculate(operation: Operation, base: Operand, current: Operand) -> tuple[Decimal, str, str]:
    check_stock_sum(operation, current.metric)
    check_periods(operation, base.period, current.period)
    if normalize(base.metric) != normalize(current.metric) or normalize(base.entity) != normalize(current.entity):
        raise Abstain("Las cifras corresponden a indicadores o entidades distintos.")
    if operation == "participation":
        flows = {"utilidad neta", "ingresos intereses", "ingresos totales", "gastos operacion"}
        if not (base.additive and current.additive) and normalize(current.metric) not in flows:
            raise Abstain("La participación temporal exige una magnitud de flujo aditiva, como la utilidad neta.")
        scope = lambda item: (item.citation.doc_id, item.citation.pdf_page, item.citation.evidence_id.rsplit(":", 2)[0])
        if (scope(base) != scope(current) or base.unit.name != "moneda"
                or not all(re.search(r":\d+:\d+:\d+:\d+$", item.citation.evidence_id)
                           for item in (base, current))):
            raise Abstain("La participación exige cifras monetarias de la misma tabla y una base común.")
    if (base.unit.name, base.unit.currency) != (current.unit.name, current.unit.currency):
        currency_a, currency_b = base.unit.currency or "", current.unit.currency or ""
        if ":" in currency_a and ":" in currency_b and currency_a.split(":", 1)[0] == currency_b.split(":", 1)[0]:
            raise Abstain("La moneda común no está acreditada entre las fuentes; la leyenda de cada tabla solo aplica a sus propias cifras.")
        raise Abstain("Las unidades o monedas de los operandos son incompatibles.")
    if base.definition != current.definition:
        raise Abstain("Las notas de las fuentes no acreditan la misma definición del indicador.")
    if base.note or current.note:
        if not base.comparable_basis or base.comparable_basis != current.comparable_basis:
            raise Abstain("La fuente advierte una reexpresión o cambio de perímetro sin una base común verificada.")
    elif normalize(base.basis) != normalize(current.basis):
        raise Abstain("Las fuentes identifican bases contables distintas.")

    with localcontext() as context:
        context.prec = 50
        b = base.value * base.unit.scale / current.unit.scale
        a = current.value
        unit = current.unit.label
        if operation == "percent_change":
            if b <= 0:
                raise Abstain("La variación porcentual requiere una base mayor que cero.")
            return (a - b) / b * 100, "%", "(A − B) ÷ B × 100"
        if operation == "participation":
            if b <= 0:
                raise Abstain("La participación exige un acumulado mayor que cero.")
            return a / b * 100, "% de participación", "A ÷ B × 100"
        if operation == "ratio":
            if b == 0:
                raise Abstain("La razón requiere un denominador distinto de cero.")
            return a / b, "veces", "A ÷ B"
        if operation == "sum":
            start = lambda p: p.year * 12 + p.end - p.months
            end = lambda p: p.year * 12 + p.end
            if not (base.additive and current.additive) or max(start(base.period), start(current.period)) < min(end(base.period), end(current.period)):
                raise Abstain("La suma exige una magnitud aditiva y periodos sin solapamiento.")
            return a + b, unit, "A + B"
        return a - b, "puntos porcentuales" if unit == "%" else unit, "A − B"


def display(value):
    with localcontext() as context:
        context.prec = 50
        shown = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        return f"{abs(shown) if not shown else shown:f}".rstrip("0").rstrip(".")
