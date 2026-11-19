"""Lectura bajo demanda de cifras y encabezados en el monolito V3."""
import re
from contextlib import closing
from decimal import Decimal

import pymupdf

from .corpus import Corpus, PDF_LOCK, SourceRef, terms
from .finance import Abstain, Operand, PERIOD, Period, Unit, decimal_from_source, local_period, normalize
from .market_table import MARKET_ROW, is_market_metric, market_cells

ENTITY = re.compile(r"(?im)^\s*(?:tabla comparativa\s*[-–]\s*)?(?:entidad\s*:\s*([^\n|]+)|((?:grupo|banco)\s+[^\n|]+?)\s+(?:no\s+)?consolidad[oa]\b|(GFNorte)\s*[-–,])")
BASIS = re.compile(r"\b(?:no\s+)?consolidad[oa](?:\s+con\s+subsidiarias)?\b", re.I)
CURRENCY = re.compile(r"\b(?:(millones|miles)(?:\s+de)?\s+)?(MXN|USD|EUR|pesos(?:\s+mexicanos)?|d[oó]lares(?:\s+estadounidenses)?|euros)\b", re.I)
NOTE = re.compile(r"\b(?:desconsolid\w*|reexpres\w*|cambio de perímetro|operaciones discontinuadas)\b", re.I)
BINEO_EVENT = re.compile(r"\bdesconsolid\w*\s+(?:(?:la|su)\s+operaci[oó]n\s+)?de\s+Bineo\b", re.I)
COMMON = re.compile(r"(?im)^base comparable\s*:\s*([^\n|]+)")
ADDITIVE = re.compile(r"(?im)^magnitud aditiva\s*:\s*([^\n|]+)")
TABULAR_LINES = re.compile(r"\s+")
INDICATORS = re.compile(r"indicadores financieros\s+([^\n|]+)", re.I)
ROW_NOTE = re.compile(r"\s+\((\d{1,2})\)\s*$")


class UnverifiedBasis(Abstain):
    def __init__(self, reason, citation):
        super().__init__(reason)
        self.citation = citation


def find_candidates(corpus: Corpus, metric: str, period: Period, other: Period | None = None):
    """BM25 de P0 con cobertura por periodo. Un encabezado puede vivir en otro fragmento."""
    tokens = terms(metric)
    if not tokens:
        return []
    pattern = " AND ".join(f'"{token}"' for token in tokens[:16])
    short_indicator = len(tokens) == 1 and len(tokens[0]) <= 5
    with closing(corpus.connect()) as db:
        rows = db.execute("""
            SELECT doc, page, fragment, body FROM chunks WHERE chunks MATCH ?
            ORDER BY bm25(chunks) ASC, doc, page, fragment LIMIT 1200
        """, (pattern,)).fetchall()
        # El índice existente también permite localizar encabezados separados de la fila.
        headings = db.execute("""
            SELECT doc, page, body FROM chunks WHERE chunks MATCH ?
            ORDER BY bm25(chunks) ASC LIMIT 600
        """, ('"consolidado" OR "consolidada"',)).fetchall()
        indicator_pages = db.execute("""
            SELECT doc, page, body FROM chunks WHERE chunks MATCH ?
            ORDER BY bm25(chunks) ASC LIMIT 300
        """, ('"indicadores financieros"',)).fetchall() if short_indicator else []
        market_pages = db.execute("""
            SELECT doc, page, body FROM chunks WHERE chunks MATCH ?
            ORDER BY bm25(chunks) ASC, doc, page, fragment LIMIT 400
        """, ('("informacion" AND "accion" AND "grupo") OR "bursatiles"',)).fetchall() if is_market_metric(metric) else []
    pages = {}
    header_scores = {}
    for row in headings:
        codes = {local_period(m) for m in PERIOD.finditer(row["body"])}
        if period in codes:
            key = (row["doc"], row["page"])
            score = 1 + int(other in codes) + int(bool(CURRENCY.search(row["body"])))
            header_scores[key] = max(score, header_scores.get(key, 0))
    for row in indicator_pages:
        codes = {local_period(m) for m in PERIOD.finditer(row["body"])}
        if period in codes:
            key = (row["doc"], row["page"])
            header_scores[key] = 4 + int(other in codes)
    for row in market_pages:
        codes = {local_period(m) for m in PERIOD.finditer(row["body"])}
        if period in codes:
            key = (row["doc"], row["page"])
            header_scores[key] = max(header_scores.get(key, 0), 4 + int(other in codes))
    for row in rows:
        key = (row["doc"], row["page"])
        codes = {local_period(m) for m in PERIOD.finditer(row["body"])}
        if period not in codes and not header_scores.get(key):
            continue
        score = header_scores.get(key, 0)
        if key not in pages:
            pages[key] = score, SourceRef(doc_id=key[0], pdf_page=key[1], fragment=row["fragment"])
    return [ref for _, ref in sorted(pages.values(), key=lambda item: -item[0])][:8]


def currency_key(name):
    key = normalize(name)
    return {"pesos mexicanos": "MXN", "dolares estadounidenses": "USD", "dolares": "dólares",
            "euros": "EUR", "pesos": "pesos"}.get(key, key.upper())


def unit_from_context(text, original, scope):
    if original.rstrip().rstrip(")").endswith("%"):
        return Unit("tasa", None, Decimal(1), "%")
    matches = {(str(scale or "").lower(), currency.lower()) for scale, currency in CURRENCY.findall(text)}
    if len(matches) != 1:
        raise Abstain("La unidad o moneda de la cifra es ambigua.")
    scale, currency = matches.pop()
    code = currency_key(currency)
    if code in {"pesos", "dólares"}:
        # La leyenda de una tabla aplica únicamente a sus propios operandos.
        code = f"{code}:{scope}"
    label = f"{scale} de {currency}" if scale else currency
    return Unit("moneda", code, Decimal({"millones": 1_000_000, "miles": 1000, "": 1}[scale]), label)


def make_operand(citation, metric, period, original, context, notes, scope, comma_grouping, note_citation,
                 *, indicators=None, definition=None, market_entity=None):
    entities = {normalize(next(group for group in m.groups() if group)): next(group for group in m.groups() if group)
                for m in ENTITY.finditer(context)}
    bases = {normalize(m.group()): m.group() for m in BASIS.finditer(context)}
    if indicators and definition:
        if entities and set(entities) != {normalize(indicators)}:
            raise Abstain("El encabezado y la sección de indicadores identifican entidades distintas.")
        entities = {normalize(indicators): indicators}
        bases = {"indicadores": "indicadores financieros con metodología explícita"}
    if market_entity:
        entities = {normalize(market_entity): market_entity}
        bases = {"mercado": "capitalización de la acción del grupo"}
    if len(entities) != 1 or len(bases) != 1:
        raise Abstain("La entidad o la base de consolidación no se puede identificar inequívocamente.")
    note = "La fuente advierte una reexpresión o cambio de perímetro." if NOTE.search(notes) else None
    basis = COMMON.search(notes)
    if note and not basis:
        # Nombrar un evento solo cuando el sustantivo y la entidad figuran juntos.
        subject = " (desconsolidación de Bineo)" if note_citation and BINEO_EVENT.search(note_citation.snippet) else ""
        raise UnverifiedBasis(f"La fuente advierte un cambio de perímetro{subject} sin base común verificada.",
                              note_citation)
    additive = any(normalize(label) == normalize(metric) for label in ADDITIVE.findall(context))
    return Operand(citation=citation, metric=metric, entity=next(iter(entities.values())), period=period,
                   unit=unit_from_context(context, original, scope), basis=next(iter(bases.values())),
                   original=original, value=decimal_from_source(original, comma_grouping=comma_grouping),
                   comparable_basis=normalize(basis[1]) if basis else None, note=note, additive=additive,
                   note_citation=note_citation, definition=definition)


def exact_header(value, period):
    match = PERIOD.fullmatch(value.strip())
    return bool(match and local_period(match) == period)


def metric_label(cell):
    return normalize(ROW_NOTE.sub("", cell))


def defined_metric(page, label, metric):
    marker = ROW_NOTE.search(label)
    if marker is None:
        return None
    pattern = rf"^\s*{marker[1]}\.\s*{re.escape(metric)}\s*=\s*(.+)"
    lines = re.findall(pattern, page.get_text(sort=True), flags=re.I | re.M)
    if len(lines) != 1:
        raise Abstain("La nota numerada no acredita inequívocamente la definición del indicador.")
    return TABULAR_LINES.sub(" ", lines[0].strip().rstrip(".").casefold())


def table_operands(page, period, metric, citation, notes, note_citation):
    candidates = []
    matched_rows = False
    page_context = "\n".join(line for line in page.get_text().splitlines()
                             if ENTITY.match(line) or CURRENCY.fullmatch(line.strip(" ()")) or ADDITIVE.match(line))
    for table_no, table in enumerate(page.find_tables().tables):
        rows = [[cell or "" for cell in row] for row in table.extract()]
        scope = f"{citation.doc_id}:{citation.pdf_page}:{table_no}"
        first_metric = next((i for i, row in enumerate(rows) if row and metric_label(row[0]) == normalize(metric)), None)
        if first_metric is None:
            continue
        matched_rows = True
        header_rows = rows[:first_metric]
        section = next(((i, match[1]) for i, row in reversed(list(enumerate(header_rows)))
                        if row and (match := INDICATORS.fullmatch(row[0].strip()))), None)
        if section:
            header_rows = header_rows[section[0]:]
        header_context = "\n".join(row[0] for row in header_rows[:4] if row)
        context = header_context if ENTITY.search(header_context) and CURRENCY.search(header_context) else header_context + "\n" + page_context
        columns = {col for row in header_rows[:4] for col, value in enumerate(row)
                   if col and exact_header(value, period)}
        if len(columns) > 1:
            raise Abstain("No se pudo identificar una columna inequívoca para el periodo en la tabla.")
        if not columns:
            continue
        col = columns.pop()
        # No interpretar columnas comparativas que mezclan periodos.
        column_periods = {local_period(match) for row in header_rows[:4] if col < len(row)
                          for match in PERIOD.finditer(row[col])}
        if column_periods != {period}:
            raise Abstain("La columna mezcla periodos y no acredita un valor comparable.")
        cells = [(i, row[0], row[col].strip()) for i, row in enumerate(rows[first_metric:], start=first_metric)
                 if len(row) > col and metric_label(row[0]) == normalize(metric)]
        if len(cells) != 1:
            continue
        row_number, label, original = cells[0]
        definition = defined_metric(page, label, metric)
        grouping = any(re.fullmatch(r"[+-]?\d{1,3}(?:,\d{3}){2,}(?:\.\d+)?", cell.strip())
                       for row in rows for cell in row)
        if not grouping:
            page_text = page.get_text()
            grouping = bool(re.search(r"\d\.\d{1,2}\s*%", page_text)
                            and not re.search(r"\d,\d{1,2}\s*%", page_text))
        evidence = citation.model_copy(update={
            "evidence_id": f"{scope}:{row_number}:{col}",
            "snippet": f"{label} | {period.label} | {original}",
        })
        candidates.append(make_operand(evidence, metric, period, original, context, notes, scope,
                                       grouping, note_citation, indicators=section[1] if section else None,
                                       definition=definition))
    if len(candidates) > 1:
        raise Abstain("Varias celdas de la página pueden corresponder al indicador.")
    if matched_rows and not candidates:
        raise Abstain("No se pudo identificar una columna inequívoca para el periodo en la tabla.")
    return candidates[0] if candidates else None


def market_operand(document, page, citation, metric, period, other, requested_currency, requested_scale,
                   notes, note_citation):
    inline = MARKET_ROW.fullmatch(metric)
    if inline:
        unit = CURRENCY.fullmatch(inline[1].strip())
        if unit is None:
            raise Abstain("La unidad de capitalización solicitada no es inequívoca.")
        scale, currency = unit.groups()
        inline_currency = currency_key(currency)
        inline_scale = scale.lower() if scale else None
        if ((requested_currency and requested_currency != inline_currency)
                or (requested_scale and inline_scale != requested_scale)):
            raise Abstain("La consulta especifica unidades de capitalización incompatibles.")
        requested_currency, requested_scale = inline_currency, inline_scale

    def matches_unit(label):
        unit = CURRENCY.fullmatch(label.strip())
        if unit is None:
            return False
        scale, currency = unit.groups()
        return ((not requested_currency or currency_key(currency) == requested_currency)
                and (not requested_scale or requested_scale == (scale or "").lower()))

    cell = market_cells(page, period, other, matches_unit)
    indices = [page.number] + ([page.number - 1] if page.number else [])
    entities = set()
    for index in indices:
        text = document[index].get_text(sort=True)
        entities.update(next(item for item in match.groups() if item) for match in ENTITY.finditer(text))
    if len({normalize(entity) for entity in entities}) != 1:
        raise Abstain("No se pudo vincular el encabezado bursátil con una entidad única.")
    scope = f"{citation.doc_id}:{citation.pdf_page}:bursatil:{cell.header}"
    source = citation.model_copy(update={
        "evidence_id": f"{scope}:{cell.row}:{cell.column}",
        "snippet": f"{cell.label} | {period.label} | {cell.value}",
    })
    page_text = page.get_text(sort=True)
    comma_grouping = bool(re.search(r"(?<![\d.,])\d{1,3}(?:,\d{3})+(?:\.\d+)", page_text)
                          or re.search(r"(?<![\d.,])\d{1,3}(?:,\d{3}){2,}(?![\d.,])", page_text))
    has_decimal_comma = re.search(r"(?<![\d.,])\d{1,3}(?:\.\d{3})+,\d+", page_text)
    if comma_grouping and has_decimal_comma and ("," in cell.value or "." in cell.value):
        raise Abstain("La página mezcla convenciones numéricas y la escala del importe es ambigua.")
    return make_operand(source, metric, period, cell.value, cell.unit, notes, scope,
                        comma_grouping, note_citation, market_entity=min(entities))


def read_operand(corpus, ref, metric, period, *, other=None, requested_currency=None, requested_scale=None):
    citation = corpus.read_source(ref)
    _, original = corpus.original(ref.doc_id)
    with PDF_LOCK, pymupdf.open(stream=original, filetype="pdf") as document:
        page = document[ref.pdf_page - 1]
        indices = sorted({*range(min(len(document), 4)), *range(max(0, page.number - 1), min(len(document), page.number + 2))})
        note_hits = []
        suspected_pages = []
        for index in indices:
            note_page = document[index]
            if NOTE.search(note_page.get_text()):
                suspected_pages.append(index)
            for *_, paragraph, _, kind in note_page.get_text("blocks"):
                excerpt = " ".join(paragraph.split())
                if not kind and NOTE.search(excerpt) and re.search(r"[.!?]$", excerpt):
                    score = (bool(re.search(r"\bno (?:son |es )?comparable", excerpt, re.I)),
                             bool(BINEO_EVENT.search(excerpt)), index == page.number)
                    note_hits.append((score, index, excerpt))
        note_citation = None
        notes = page.get_text()
        if note_hits:
            _, index, excerpt = max(note_hits, key=lambda hit: hit[0])
            notes += "\n" + document[index].get_text()
            note_citation = citation.model_copy(update={
                "pdf_page": index + 1, "evidence_id": f"{ref.doc_id}:{index + 1}:nota",
                "snippet": excerpt,
            })
        elif suspected_pages:
            notes += "\n" + document[suspected_pages[0]].get_text()
        if is_market_metric(metric):
            return market_operand(document, page, citation, metric, period, other,
                                  requested_currency, requested_scale, notes, note_citation)
        selected = table_operands(page, period, metric, citation, notes, note_citation)
        if selected:
            return selected
        # Aceptar texto solo si identifica los tres campos en una misma línea,
        # y si la línea contiene un único valor, no una lista ni una fila aplanada.
        page_text = page.get_text()
        passages = []
        for line_no, line in enumerate(page_text.splitlines()):
            pieces = [p.strip() for p in line.split("|")]
            if len(pieces) == 3 and normalize(pieces[0]) == normalize(metric) and exact_header(pieces[1], period):
                passages.append((line_no, line, pieces[2]))
        if len(passages) > 1:
            raise Abstain("Varios pasajes de la página pueden corresponder al indicador.")
        if passages:
            line_no, line, value = passages[0]
            scope = f"{citation.doc_id}:{citation.pdf_page}:text"
            evidence = citation.model_copy(update={
                "evidence_id": f"{scope}:{line_no}", "snippet": TABULAR_LINES.sub(" ", line).strip(),
            })
            return make_operand(evidence, metric, period, value, page_text, notes, scope, False, note_citation)
    raise Abstain("La página no acredita una celda o un pasaje inequívoco para este periodo.")
