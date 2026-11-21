"""Resolver expresiones de calendario a periodos de los operandos."""
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from .finance import PERIOD, Period, local_period

ORDINAL = {"primer": 1, "primero": 1, "segundo": 2, "tercer": 3, "tercero": 3, "cuarto": 4}
QUARTER = "|".join(sorted(ORDINAL, key=len, reverse=True))
MONTHS = {name: index for index, name in enumerate(
    "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split(), 1
)}
MONTH = "|".join(MONTHS)
YEAR = r"(?:\s+de(?:l\s+año)?\s+(?P<year>20\d{2})|\s+(?P<relative>de (?:ese|dicho)(?: mismo)? año|del mismo año|del año (?:anterior|siguiente|mismo)))?"
CALENDAR = re.compile(
    rf"\b(?:trimestre\s+)?(?P<first>{MONTH})\s*(?:[-–—]|\ba\b|\by\b)\s*(?P<last>{MONTH})\b{YEAR}"
    rf"|\b(?:(?P<ordinal>{QUARTER})(?:\s+(?P<quarter>trimestres?|semestre))?\b"
    rf"|primeros\s+(?P<size>tres|seis|nueve|doce)\s+meses\b"
    rf"|(?P<closing>cierre\s+de)\s+(?P<month>{MONTH})\b"
    rf"|acumulad[oa]\s+(?:a|al|hasta)\s+(?P<cutoff>{MONTH})\b"
    rf"|(?:mism[oa]|igual)\s+(?P<same>acumulado|intervalo|periodo|trimestre)\b"
    rf"|(?P<next>trimestre\s+(?:siguiente|(?:previamente |antes )mencionado)|periodo\s+correspondiente)\b)"
    + YEAR.replace("?P<year>", "?P<endyear>").replace("?P<relative>", "?P<endrelative>"),
    re.I,
)
COORDINATION = re.compile(r"\s+(?:y|a|al)\s+(?:(?:el|la)\s+)?", re.I)
REPORT_PREFIX = re.compile(
    r"\b(?:reporte|informe|tabla|documento|publicacion)\b[^,;.!?]{0,55}\bdel?\s*$", re.I
)


@dataclass(frozen=True)
class TemporalMention:
    text: str
    start: int
    end: int
    period: Period | None
    role: Literal["operand", "report"]
    kind: Literal["interval", "closing"]
    reference: int | None
    status: Literal["resolved", "ambiguous", "unsupported"]


def fold(text):
    return "".join(char for char in unicodedata.normalize("NFKD", text.casefold())
                   if not unicodedata.combining(char))


def calendar_label(start, end):
    if start in (1, 4, 7, 10) and end == start + 2:
        return f"{end // 3}T"
    if start == 1 and end in (6, 9, 12):
        return f"{end}M"
    if start == 7 and end == 12:
        return "2S"
    return None


def resolve_periods(text: str) -> tuple[TemporalMention, ...]:
    """Resolver únicamente vínculos explícitos o años con candidato único."""
    tokens = sorted([*PERIOD.finditer(text), *CALENDAR.finditer(text)], key=lambda match: match.start())
    found = []
    for i, match in enumerate(tokens):
        fields = match.groupdict()
        previous = [item for item in found if item.period and item.role == "operand"]
        role = "report" if REPORT_PREFIX.search(fold(text[max(0, match.start() - 85):match.start()])) else "operand"
        kind = "closing" if fields.get("closing") or re.search(r"\bcierre\s+de\s*$", text[:match.start()], re.I) else "interval"
        if not fields:
            found.append(TemporalMention(match[0], match.start(), match.end(), local_period(match), role,
                                         kind, None, "resolved"))
            continue
        values = {key: fold(value) for key, value in fields.items() if value}
        explicit = values.get("year") or values.get("endyear")
        relative = values.get("relative") or values.get("endrelative")
        anchor = None
        year = int(explicit) if explicit else None
        label = None
        following = tokens[i + 1] if i + 1 < len(tokens) else None
        coordinated = following is not None and COORDINATION.fullmatch(text[match.end():following.start()])
        if values.get("ordinal"):
            ordinal = ORDINAL[values["ordinal"]]
            shape = values.get("quarter")
            if not shape and coordinated:
                shape = following.groupdict().get("quarter")
            if shape == "semestre":
                label = {1: "6M", 2: "2S"}.get(ordinal)
            elif shape or explicit or relative:
                label = f"{ordinal}T"
            else:
                continue
        elif "first" in values:
            label = calendar_label(MONTHS[values["first"]], MONTHS[values["last"]])
        elif "month" in values:
            end = MONTHS[values["month"]]
            label = f"{end // 3}T" if end % 3 == 0 else None
        elif "cutoff" in values:
            end = MONTHS[values["cutoff"]]
            label = calendar_label(1, end) if end != 3 else "3M"
        elif "size" in values:
            label = {"tres": "3M", "seis": "6M", "nueve": "9M", "doce": "12M"}[values["size"]]
        else:
            candidates = {item.period: item for item in previous if (
                (values.get("same") != "acumulado" or item.period.kind == "ytd")
                and (values.get("same") != "trimestre" and "trimestre" not in values.get("next", "")
                     or item.period.kind == "quarter")
            )}
            if len(candidates) == 1:
                anchor = next(iter(candidates.values()))
                base = anchor.period
                label = base.label[:-2]
                year = year or base.year
                if values.get("next") == "trimestre siguiente":
                    label = f"{base.end // 3 % 4 + 1}T"
                    year += int(base.end == 12)
        if relative:
            years = {item.period.year: item for item in previous}
            if anchor is None and len(years) == 1:
                anchor = next(iter(years.values()))
            year = anchor.period.year + ("siguiente" in relative) - ("anterior" in relative) if anchor else None
        elif year is None and not ("same" in values or "next" in values):
            if coordinated:
                next_fields = following.groupdict()
                next_year = next_fields.get("year") or next_fields.get("endyear")
                if not next_fields:
                    year = local_period(following).year
                elif next_year:
                    year = int(next_year)
            if year is None:
                years = {item.period.year: item for item in previous}
                if not years:
                    years = {item.period.year: item for item in found if item.period and item.role == "report"}
                if len(years) == 1:
                    anchor = next(iter(years.values()))
                    year = anchor.period.year
        period = local_period(PERIOD.fullmatch(f"{label}{year % 100:02}")) if label and year else None
        reference = anchor.start if anchor else following.start() if coordinated and year and not explicit else None
        found.append(TemporalMention(match[0], match.start(), match.end(), period, role, kind, reference,
                                     "resolved" if period else "ambiguous" if label or "same" in values or "next" in values
                                     else "unsupported"))
    return tuple(found)


def normalized_periods(text: str, mentions: tuple[TemporalMention, ...]) -> str:
    """Conservar el periodo documental al citarlo, fuera de la secuencia de operandos."""
    parts = []
    cursor = 0
    operands = {item.period for item in mentions if item.period and item.role == "operand"}
    for mention in mentions:
        if not mention.period:
            continue
        label = mention.period.label
        if mention.role == "report" and (len(operands) >= 2 or not re.search(
            r"\brespecto\s+(?:a|al|del?)\b", text, re.I
        )):
            label = f"reporte({mention.period.year}/{mention.period.end:02})"
        parts.extend((text[cursor:mention.start], label))
        cursor = mention.end
    return "".join([*parts, text[cursor:]])


def normalize_periods(text: str) -> str:
    return normalized_periods(text, resolve_periods(text))
