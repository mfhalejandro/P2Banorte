"""Lectura bajo demanda de cifras y encabezados en el monolito V3."""
import re
from contextlib import closing
from decimal import Decimal

import pymupdf

from .corpus import Corpus, PDF_LOCK, SourceRef, terms
from .finance import Abstain, Operand, PERIOD, Period, Unit, decimal_from_source, local_period, normalize

ENTITY = re.compile(r"(?im)^(?:entidad\s*:\s*([^\n|]+)|((?:grupo|banco)\s+[^\n|]+?)\s+(?:no\s+)?consolidad[oa]\b|(GFNorte)\s*[-–])")
BASIS = re.compile(r"\b(?:no\s+)?consolidad[oa](?:\s+con\s+subsidiarias)?\b", re.I)
CURRENCY = re.compile(r"\b(?:(millones|miles)(?:\s+de)?\s+)?(MXN|USD|EUR|pesos(?:\s+mexicanos)?|dólares(?:\s+estadounidenses)?|euros)\b", re.I)
NOTE = re.compile(r"\b(?:desconsolida\w*|reexpres\w*|cambio de perímetro|operaciones discontinuadas)\b", re.I)
COMMON = re.compile(r"(?im)^base comparable\s*:\s*([^\n|]+)")
ADDITIVE = re.compile(r"(?im)^magnitud aditiva\s*:\s*([^\n|]+)")
TABULAR_LINES = re.compile(r"\s+")


def find_candidates(corpus: Corpus, metric: str, period: Period, other: Period | None = None):
    """BM25 de P0 con cobertura por periodo. Un encabezado puede vivir en otro fragmento."""
    tokens = terms(metric)
    if not tokens:
        return []
    pattern = " AND ".join(f'"{token}"' for token in tokens[:16])
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
    pages = {}
    header_scores = {}
    for row in headings:
        codes = {local_period(m) for m in PERIOD.finditer(row["body"])}
        if period in codes:
            key = (row["doc"], row["page"])
            score = 1 + int(other in codes) + int(bool(CURRENCY.search(row["body"])))
            header_scores[key] = max(score, header_scores.get(key, 0))
    for row in rows:
        key = (row["doc"], row["page"])
        codes = {local_period(m) for m in PERIOD.finditer(row["body"])}
        if period not in codes and not header_scores.get(key):
            continue
        score = header_scores.get(key, 0)
        if key not in pages:
            pages[key] = score, SourceRef(doc_id=key[0], pdf_page=key[1], fragment=row["fragment"])
    return [ref for _, ref in sorted(pages.values(), key=lambda item: -item[0])][:8]


def unit_from_context(text, original, scope):
    if original.rstrip().rstrip(")").endswith("%"):
        return Unit("tasa", None, Decimal(1), "%")
    matches = {(str(scale or "").lower(), currency.lower()) for scale, currency in CURRENCY.findall(text)}
    if len(matches) != 1:
        raise Abstain("La unidad o moneda de la cifra es ambigua.")
    scale, currency = matches.pop()
    if currency == "pesos":
        # Una leyenda compartida de tabla prueba unidad común aunque omita el código ISO.
        code = "pesos:" + scope
    else:
        code = {"pesos mexicanos": "MXN", "dólares estadounidenses": "USD", "euros": "EUR"}.get(currency, currency.upper())
        if code == "DÓLARES":
            code = "dólares:" + scope
    label = f"{scale} de {currency}" if scale else currency
    return Unit("moneda", code, Decimal({"millones": 1_000_000, "miles": 1000, "": 1}[scale]), label)


def make_operand(citation, metric, period, original, context, notes, scope, comma_grouping, note_citation):
    entities = {normalize(next(group for group in m.groups() if group)): next(group for group in m.groups() if group)
                for m in ENTITY.finditer(context)}
    bases = {normalize(m.group()): m.group() for m in BASIS.finditer(context)}
    if len(entities) != 1 or len(bases) != 1:
        raise Abstain("La entidad o la base de consolidación no se puede identificar inequívocamente.")
    note = "La fuente advierte una reexpresión o cambio de perímetro." if NOTE.search(notes) else None
    basis = COMMON.search(notes)
    additive = any(normalize(label) == normalize(metric) for label in ADDITIVE.findall(context))
    return Operand(citation=citation, metric=metric, entity=next(iter(entities.values())), period=period,
                   unit=unit_from_context(context, original, scope), basis=next(iter(bases.values())),
                   original=original, value=decimal_from_source(original, comma_grouping=comma_grouping),
                   comparable_basis=normalize(basis[1]) if basis else None, note=note, additive=additive,
                   note_citation=note_citation)


def exact_header(value, period):
    match = PERIOD.fullmatch(value.strip())
    return bool(match and local_period(match) == period)


def table_operands(page, period, metric, citation, notes, note_citation):
    candidates = []
    matched_rows = False
    page_context = "\n".join(line for line in page.get_text().splitlines()
                             if ENTITY.match(line) or CURRENCY.fullmatch(line.strip(" ()")) or ADDITIVE.match(line))
    for table_no, table in enumerate(page.find_tables().tables):
        rows = [[cell or "" for cell in row] for row in table.extract()]
        scope = f"{citation.doc_id}:{citation.pdf_page}:{table_no}"
        first_metric = next((i for i, row in enumerate(rows) if row and normalize(row[0]) == normalize(metric)), None)
        if first_metric is None:
            continue
        matched_rows = True
        header_rows = rows[:first_metric]
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
        cells = [row[col].strip() for row in rows[first_metric:]
                 if len(row) > col and normalize(row[0]) == normalize(metric)]
        if len(cells) != 1:
            continue
        original = cells[0]
        grouping = any(re.fullmatch(r"[+-]?\d{1,3}(?:,\d{3}){2,}(?:\.\d+)?", cell.strip())
                       for row in rows for cell in row)
        if not grouping:
            page_text = page.get_text()
            grouping = bool(re.search(r"\d\.\d{1,2}\s*%", page_text)
                            and not re.search(r"\d,\d{1,2}\s*%", page_text))
        evidence = citation.model_copy(update={
            "evidence_id": f"{scope}:{first_metric}:{col}",
            "snippet": f"{metric} | {period.label} | {original}",
        })
        candidates.append(make_operand(evidence, metric, period, original, context, notes, scope,
                                       grouping, note_citation))
    if len(candidates) > 1:
        raise Abstain("Varias celdas de la página pueden corresponder al indicador.")
    if matched_rows and not candidates:
        raise Abstain("No se pudo identificar una columna inequívoca para el periodo en la tabla.")
    return candidates[0] if candidates else None


def read_operand(corpus, ref, metric, period):
    citation = corpus.read_source(ref)
    _, original = corpus.original(ref.doc_id)
    with PDF_LOCK, pymupdf.open(stream=original, filetype="pdf") as document:
        page = document[ref.pdf_page - 1]
        indices = sorted({*range(min(len(document), 4)), *range(max(0, page.number - 1), min(len(document), page.number + 2))})
        note_hits = [(index, NOTE.search(document[index].get_text())) for index in indices]
        found_notes = [index for index, match in note_hits if match]
        note_citation = None
        notes = page.get_text()
        if found_notes:
            index = page.number if page.number in found_notes else found_notes[0]
            notes += "\n" + document[index].get_text()
            note_citation = citation.model_copy(update={
                "pdf_page": index + 1, "evidence_id": f"{ref.doc_id}:{index + 1}:nota",
                "snippet": "Nota sobre base contable o perímetro.",
            })
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
