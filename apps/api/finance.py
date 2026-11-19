"""Reglas de negocio para operandos comprobados en el PDF."""
import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from typing import Literal

from .corpus import Citation, terms

Operation = Literal["difference", "percent_change", "ratio", "sum"]
PERIOD = re.compile(r"(?<!\w)(?:([1-4])\s*T|([369])\s*M|(12)\s*M)\s*[- ]?\s*(20\d{2}|\d{2})(?!\w)", re.I)


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
    quarter, ytd, full, digits = match.groups()
    year = int(digits) + (2000 if len(digits) == 2 else 0)
    if quarter:
        return Period(f"{quarter}T{year % 100:02}", "quarter", 3, year, int(quarter) * 3)
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


def calculate(operation: Operation, base: Operand, current: Operand) -> tuple[Decimal, str, str]:
    if normalize(base.metric) != normalize(current.metric) or normalize(base.entity) != normalize(current.entity):
        raise Abstain("Las cifras corresponden a indicadores o entidades distintos.")
    if (base.period.kind, base.period.months) != (current.period.kind, current.period.months):
        raise Abstain("Los periodos tienen distinto tipo o duración, por ejemplo trimestre frente a acumulado.")
    if (base.unit.name, base.unit.currency) != (current.unit.name, current.unit.currency):
        raise Abstain("Las unidades o monedas de los operandos son incompatibles.")
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
