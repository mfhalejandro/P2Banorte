"""Asociación geométrica de filas de capitalización con encabezados de periodo."""
import re
from dataclasses import dataclass

from .finance import Abstain, PERIOD, decimal_from_source, local_period, normalize

MARKET_ROW = re.compile(r"^capitalizaci[oó]n\s+de\s+mercado\s*\(([^()]+)\)", re.I)


def is_market_metric(metric):
    return normalize(metric.partition("(")[0]) == "capitalizacion mercado"


@dataclass(frozen=True)
class MarketCell:
    label: str
    unit: str
    value: str
    header: int
    row: int
    column: int


def word_rows(page):
    """Agrupar caracteres impresos por línea sin confiar en celdas fusionadas."""
    def middle(word):
        return (word[1] + word[3]) / 2

    rows = []
    for word in sorted(page.get_text("words"), key=lambda word: (middle(word), word[0])):
        if not rows or abs(middle(word) - middle(rows[-1][0])) > min(3, (word[3] - word[1]) * .35):
            rows.append([])
        rows[-1].append(word)
    return [sorted(row, key=lambda word: word[0]) for row in rows]


def period_columns(row, text):
    pieces = []
    offset = 0
    for word in row:
        end = offset + len(word[4])
        pieces.append((offset, end, word[0], word[2]))
        offset = end + 1
    columns = []
    for match in PERIOD.finditer(text):
        hits = [piece for piece in pieces if piece[0] < match.end() and piece[1] > match.start()]
        columns.append((local_period(match), (hits[0][2] + hits[-1][3]) / 2))
    return columns


def numeric_cell(words, columns, column):
    center = columns[column][1]
    gap = min(abs(center - x) for i, (_, x) in enumerate(columns) if i != column)
    values = [word[4] for word in words if abs((word[0] + word[2]) / 2 - center) < gap / 2]
    if len(values) != 1 or "%" in values[0]:
        raise Abstain("El importe no se alinea inequívocamente con una columna de periodo.")
    value = values[0]
    decimal_from_source(value, comma_grouping=True)
    return value


def market_cells(page, period, other, matches_unit):
    header = None
    results = []
    for line_number, row in enumerate(word_rows(page)):
        text = " ".join(word[4] for word in row)
        periods = list(PERIOD.finditer(text))
        if periods:
            heading = normalize(text[:periods[0].start()])
            if heading in {"informacion accion grupo", "indicadores bursatiles", "datos bursatiles grupo"}:
                header = (line_number, period_columns(row, text))
            elif heading and len(periods) >= 2:
                # Una nueva sección tabular invalida el encabezado anterior.
                header = None
        match = MARKET_ROW.match(text)
        if not match or not matches_unit(match[1]):
            continue
        if header is None:
            raise Abstain("La fila de capitalización carece de un encabezado bursátil verificable.")
        header_number, columns = header
        selected = [i for i, (label, _) in enumerate(columns) if label == period]
        if len(selected) > 1:
            raise Abstain("El periodo de capitalización tiene más de una columna posible.")
        others = [i for i, (label, _) in enumerate(columns) if label == other]
        if not selected or not others:
            continue
        if len(others) != 1 or selected == others:
            raise Abstain("El encabezado no distingue los dos periodos comparables.")
        value = numeric_cell(row, columns, selected[0])
        numeric_cell(row, columns, others[0])
        results.append(MarketCell(match[0], match[1], value, header_number, line_number, selected[0]))
    if len(results) != 1:
        raise Abstain("No se halló una sola fila de capitalización con ambos periodos y la moneda solicitada.")
    return results[0]
