"""Índice FTS5 por fragmento y acceso a las páginas originales de un corpus local."""
import argparse
import hashlib
import json
import math
import os
import re
import sqlite3
import unicodedata
from contextlib import closing
from pathlib import Path
from threading import Lock

import pymupdf
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1200)
    top_k: int = Field(default=5, ge=1, le=10)


class SourceRef(BaseModel):
    doc_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    pdf_page: int = Field(ge=1)
    fragment: int = Field(ge=0)


class Citation(BaseModel):
    doc_id: str
    filename: str
    pdf_page: int
    evidence_id: str
    snippet: str


STOP = set("a al algun alguna ante aqui como con cual cuales cuando cuanto cuantos de del el en entre es esta este hay indica la las lo los me mi muestra para por que quien se segun sobre son su sus un una unos y dice documento informe reporte explica menciona mencionan describen".split())
MAX_BYTES = 128 * 1024 * 1024
PDF_LOCK = Lock()


def terms(text):
    normalized = unicodedata.normalize("NFKD", text.casefold())
    plain = "".join(c for c in normalized if not unicodedata.combining(c))
    return list(dict.fromkeys(t for t in re.findall(r"[^\W_]+", plain)
                              if t not in STOP and len(t) > 1))


DEFINITION_PROMPT = re.compile(r"\b(?:qu[eé] es|qu[eé] significa|c[oó]mo se define)\b", re.I)
DEFINITION_LEAD = re.compile(
    r"^(?:es (?:la|el|una|un) |se refiere |se define |consiste |"
    r"(?:la |el )?(?:p[eé]rdida potencial|posibilidad|probabilidad)\b)", re.I,
)


DEFINITION_SOURCE = re.compile(
    r"\s+en\s+(?:los\s+)?(?:informes?|reportes?|documentos?)\s+de\s+(.+)$", re.I,
)


def definition_source(question):
    match = DEFINITION_SOURCE.search(question.rstrip(" ?!."))
    return set(terms(match[1])) if match else set()


def definition_topic(question):
    prompt = DEFINITION_PROMPT.search(question)
    if not prompt:
        return ""
    tail = DEFINITION_SOURCE.sub("", question[prompt.end():].rstrip(" ?!."))
    tail = re.sub(r"^\s*(?:la|el|las|los|una|un)\s+", "", tail, flags=re.I)
    return " ".join(re.findall(r"[^\W_]+", tail)[:18])


SOURCE_FIELD = r"(?:(?:el|la|los|las|su|sus|amb[oa]s)\s+)?(?:documentos?|fuentes?|p[aá]ginas?)"
SOURCE_FIELDS = rf"{SOURCE_FIELD}(?:\s+(?:y|e)\s+{SOURCE_FIELD}){{0,2}}"
PER_ITEM = r"(?:cada\s+(?:un[oa]|pol[ií]tica|elemento|punto)|la\s+definici[oó]n)"
SOURCE_VERB = r"(?:indica|señala|cita|incluye|especifica|identifica)"
PRESENTATION_CLAUSE = re.compile(
    rf"(?:{SOURCE_VERB}\s+(?:{SOURCE_FIELDS}(?:\s+(?:de|para)\s+{PER_ITEM}|\s+donde\s+(?:aparece|figura)\s+{PER_ITEM})?"
    rf"|en\s+qu[eé]\s+{SOURCE_FIELDS}\s+(?:se\s+encuentra|aparece)\s+{PER_ITEM})"
    rf"|con\s+{SOURCE_FIELDS}(?:\s+(?:de|para)\s+{PER_ITEM})?"
    r"|(?:enumera|lista)\s+(?:las\s+)?(?:pol[ií]ticas|medidas|referencias)\s+identificadas"
    r"|enum[eé]ralas|l[ií]stalas"
    r"|(?:responde|presenta(?:\s+la\s+respuesta)?|pres[eé]ntal[oa]s|enumera)\s+en\s+(?:viñetas|una\s+lista|formato\s+de\s+lista))",
    re.I,
)
CLAUSE_BOUNDARY = re.compile(rf"(?<=[.!?,])\s+|[;\n]\s*|\s+(?:y|e)\s+(?={SOURCE_VERB}\b)", re.I)
EXPLANATION_PROMPT = re.compile(
    r"^[¿\s]*(?:qu[eé]\s+(.+?)\s+se\s+(?:mencionan|describen|enumeran|indican|identifican)\b(.*)"
    r"|(?:cu[aá]les\s+son|describe|enumera|explica)\s+(.+))$", re.I,
)
LIST_MARK = re.compile(r"^([•●▪–·])(?:\s+|$)")


def documentary_query(question):
    """Eliminar solo cláusulas completas de presentación. Conservar cualquier restricción."""
    return " ".join(
        clause for clause in CLAUSE_BOUNDARY.split(question.strip())
        if clause and not PRESENTATION_CLAUSE.fullmatch(clause.strip(" ¿¡?!.,"))
    )


def explanation_terms(question):
    """Tema, entidad y restricciones presentes en la consulta documental normalizada."""
    prompt = EXPLANATION_PROMPT.match(question)
    if prompt is None:
        return set()
    subject = prompt[3] or f"{prompt[1]} {prompt[2]}"
    subject = re.sub(r"^(?:(?:las|los)\s+)?principales\s+", "", subject, flags=re.I)
    return set(terms(subject))


def page_lines(page):
    blocks = page.get_text("dict", flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES)["blocks"]
    return [
        (*line["bbox"], " ".join("".join(span["text"] for span in line["spans"]).split()))
        for block in blocks for line in block.get("lines", []) if line["dir"] == (1.0, 0.0)
    ]


def list_under_heading(page, wanted):
    lines = sorted((line for line in page_lines(page) if line[4]), key=lambda line: (line[1], line[0]))
    for left, _, _, bottom, title in lines:
        if not title.endswith(":"):
            continue
        title_terms = set(terms(title))
        if not wanted <= title_terms:
            # Un encabezado local puede omitir parte del tema que figura en la sección padre.
            section = next((body for x, y, _, end, body in reversed(lines)
                            if abs(x - left) <= 5 and 0 < bottom - end <= 230
                            and re.match(r"^\d+(?:\.\d+)*\.?\s+\D", body) and not body.endswith(".")), "")
            heading = re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", section)
            if len(wanted & title_terms) < math.ceil(len(wanted) * 0.8) or not wanted <= title_terms | set(terms(heading)):
                continue
        # La primera viñeta debe estar próxima al encabezado y en la misma columna.
        markers = [line for line in lines if left - 4 <= line[0] <= left + 36
                   and line[1] >= bottom - 2 and LIST_MARK.match(line[4])]
        if not markers or markers[0][1] - bottom > 24:
            continue
        indent = markers[0][0]
        markers = [line for line in markers if abs(line[0] - indent) <= 5]
        items = []
        for index, (left_mark, top, right, mark_bottom, marked) in enumerate(markers[:6]):
            if top - bottom > 24:
                break
            content = LIST_MARK.sub("", marked).strip()
            text_left = left_mark
            if not content:
                first = min((line for line in lines if 0 <= line[0] - right <= 28 and abs(top - line[1]) <= 3),
                            key=lambda line: line[0], default=None)
                if first is None:
                    break
                text_left, _, _, mark_bottom, content = first
            next_top = markers[index + 1][1] if index + 1 < len(markers) else page.rect.height
            bottom = mark_bottom
            for x, y, _, end, line in lines:
                if not content.endswith((".", ";", ":", "!", "?")) and abs(x - text_left) <= 5 and bottom - 2 <= y < next_top - 2 and y - bottom <= 16:
                    if LIST_MARK.match(line) or re.fullmatch(r"\d+", line):
                        break
                    content += " " + line
                    bottom = end
            if not content.endswith((".", ";", "!", "?")) or not terms(content):
                break
            items.append(content)
        if items:
            return title + " " + " ".join(f"• {item}" for item in items)
    return ""


def definition_under_heading(page, topic):
    wanted = terms(topic)
    lines = page_lines(page)
    for left, _, _, bottom, title in lines:
        if terms(title) != wanted:
            continue
        below = sorted(
            (line for line in lines if abs(line[0] - left) <= 8 and line[1] >= bottom),
            key=lambda line: line[1],
        )
        statement = []
        for _, top, _, end, line in below[:6]:
            if top - bottom > 28 or (not statement and not DEFINITION_LEAD.match(line)):
                break
            statement.append(line)
            bottom = end
            sentence = re.match(r".+?[.!?](?=\s|$)", " ".join(statement))
            if sentence:
                return f"{title}: {sentence[0]}"
    return None


def fragments(page):
    # Mantener el orden de lectura. Conservar bloques breves juntos para dar contexto.
    words = page.get_text("text", sort=True).split()
    for start in range(0, len(words), 85):
        chunk = " ".join(words[start:start + 105])
        if chunk:
            yield chunk


class Corpus:
    def __init__(self, data, state):
        self.data = Path(data).expanduser().resolve()
        state = Path(state).expanduser().resolve()
        protected = Path(__file__).resolve().parents[2] / "docs/requirements"
        if state.is_relative_to(self.data) or state.is_relative_to(protected):
            raise ValueError("El estado debe estar fuera de los originales")
        state.mkdir(parents=True, exist_ok=True)
        self.db = state / "corpus.sqlite3"
        with closing(self.connect()) as db:
            existing = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='config'").fetchone()
            if existing:
                config = db.execute("SELECT source FROM config WHERE id=1").fetchone()
                if config is not None:
                    if config["source"] != str(self.data):
                        raise ValueError("Usa un directorio de estado propio para este corpus")
                    return
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY, source TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS docs (id TEXT PRIMARY KEY, pages INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, doc TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS files_doc ON files(doc);
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
                    body, doc UNINDEXED, page UNINDEXED, fragment UNINDEXED,
                    tokenize='unicode61 remove_diacritics 2'
                );
            """)
            db.execute("INSERT OR IGNORE INTO config VALUES (1,?)", (str(self.data),))
            if db.execute("SELECT source FROM config WHERE id=1").fetchone()[0] != str(self.data):
                raise ValueError("Usa un directorio de estado propio para este corpus")
            db.commit()

    @classmethod
    def configured(cls):
        return cls(os.getenv("RAG_DATA_DIR", "~/data"),
                   os.getenv("RAG_STATE_DIR", "~/.local/share/p2banorte"))

    def connect(self):
        conn = sqlite3.connect(self.db, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def pdf_bytes(self, relative):
        path = (self.data / relative).resolve(strict=True)
        if not path.is_relative_to(self.data) or path.suffix.lower() != ".pdf" or not path.is_file():
            raise ValueError("Documento fuera de la raíz autorizada")
        with path.open("rb") as stream:
            if os.fstat(stream.fileno()).st_size > MAX_BYTES:
                raise ValueError("PDF excede el límite de tamaño")
            data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("PDF excede el límite de tamaño")
        return data

    def index(self, limit=None):
        if not self.data.is_dir():
            raise ValueError("Directorio de PDF no disponible")
        if limit is not None and limit < 1:
            raise ValueError("El límite debe ser positivo")
        candidates = []
        for path in self.data.rglob("*"):
            if path.suffix.lower() == ".pdf" and not path.is_symlink() and path.is_file():
                try:
                    candidates.append((path.stat().st_size, path))
                except OSError:
                    # Una entrada retirada durante el descubrimiento no detiene el lote.
                    continue
        selected = [path for _, path in sorted(candidates)[:limit]]
        report = dict(discovered=len(candidates), selected=len(selected), indexed=0, reused=0, unique=0, aliases={}, failed=[])
        with closing(self.connect()) as db, db:
            # Una transacción publica el conjunto seleccionado completo. Un lector conserva
            # el índice anterior hasta el commit, incluso si la ingesta se interrumpe.
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM files")
            for path in selected:
                name = str(path.relative_to(self.data))
                db.execute("SAVEPOINT pdf")
                try:
                    data = self.pdf_bytes(name)
                    doc = hashlib.sha256(data).hexdigest()
                    known = db.execute("SELECT 1 FROM docs WHERE id=?", (doc,)).fetchone()
                    if not known:
                        with PDF_LOCK, pymupdf.open(stream=data, filetype="pdf") as pdf:
                            if pdf.needs_pass or not len(pdf):
                                raise ValueError("PDF ilegible")
                            db.execute("INSERT INTO docs VALUES (?,?)", (doc, len(pdf)))
                            for page in pdf:
                                db.executemany("INSERT INTO chunks VALUES (?,?,?,?)",
                                               ((body, doc, page.number + 1, i)
                                                for i, body in enumerate(fragments(page))))
                    db.execute("INSERT INTO files VALUES (?,?)", (name, doc))
                    report["reused" if known else "indexed"] += 1
                except (OSError, ValueError, RuntimeError) as exc:
                    db.execute("ROLLBACK TO pdf")
                    report["failed"].append({"file": name, "reason": type(exc).__name__})
                finally:
                    db.execute("RELEASE pdf")
            for path, doc in db.execute("SELECT path, doc FROM files ORDER BY path"):
                report["aliases"].setdefault(doc, []).append(path)
            report["unique"] = len(report["aliases"])
            report["aliases"] = {doc: paths for doc, paths in report["aliases"].items() if len(paths) > 1}
            for (stale,) in db.execute("SELECT id FROM docs WHERE id NOT IN (SELECT doc FROM files)").fetchall():
                db.execute("DELETE FROM chunks WHERE doc=?", (stale,))
                db.execute("DELETE FROM docs WHERE id=?", (stale,))
        return report

    def catalog(self):
        with closing(self.connect()) as db:
            return [dict(row) for row in db.execute("""
                SELECT id AS doc_id, min(path) AS filename, pages
                FROM docs JOIN files ON files.doc=docs.id GROUP BY id ORDER BY filename
            """)]

    def search_corpus(self, request: SearchRequest):
        query = documentary_query(request.query)
        topic = definition_topic(query)
        explain = explanation_terms(query) if not topic else set()
        source = definition_source(query) if topic else set()
        search_text = topic if source else query
        query_terms = [token for token in terms(search_text) if not explain or token in explain]
        tokens = query_terms[:18]
        if not tokens:
            return []
        expressions = []
        if topic:
            cues = ("se refiere a", "se define como", "consiste en", "es la posibilidad", "es la probabilidad", "pérdida potencial")
            expressions.append(" OR ".join(f'NEAR("{topic}" "{cue}", 12)' for cue in cues))
        expressions.append(" OR ".join(f'"{t}"' for t in tokens))
        with closing(self.connect()) as db:
            rows = [
                row
                for expression in expressions
                for row in db.execute("""
                    SELECT doc, page, fragment, body FROM chunks WHERE chunks MATCH ?
                    ORDER BY bm25(chunks) ASC, doc, page, fragment LIMIT ?
                """, (expression, request.top_k * 4))
            ]
        # Rechazar coincidencias débiles antes de presentarlas como evidencia.
        required = math.ceil(len(tokens) * 0.8)
        required_numbers = {t for t in query_terms if any(c.isdigit() for c in t)}
        matches = []
        for row in rows:
            common = set(tokens).intersection(terms(row["body"]))
            if len(common) >= required and required_numbers <= common:
                ref = SourceRef(doc_id=row["doc"], pdf_page=row["page"], fragment=row["fragment"])
                if ref not in matches and (
                    not explain or all((ref.doc_id, ref.pdf_page) != (match.doc_id, match.pdf_page) for match in matches)
                ):
                    matches.append(ref)
            if len(matches) == request.top_k:
                break
        return matches

    def read_source(self, ref: SourceRef, *, topic="", explain=None, source=None):
        with closing(self.connect()) as db:
            row = db.execute("""
                SELECT body
                FROM chunks WHERE doc=? AND page=? AND fragment=?
            """, (ref.doc_id, ref.pdf_page, ref.fragment)).fetchone()
        if not row:
            raise KeyError("Evidencia desconocida")
        name, data = self.original(ref.doc_id)
        body = row["body"]
        if source and not source <= set(terms(name)):
            body = ""
        elif topic or explain:
            with PDF_LOCK, pymupdf.open(stream=data, filetype="pdf") as pdf:
                page = pdf[ref.pdf_page - 1]
                body = list_under_heading(page, explain) if explain else (definition_under_heading(page, topic) or body)
        return Citation(doc_id=ref.doc_id, filename=name, pdf_page=ref.pdf_page,
                        evidence_id=f"{ref.doc_id}:{ref.pdf_page}:{ref.fragment}", snippet=body)

    def original(self, doc):
        with closing(self.connect()) as db:
            paths = db.execute("SELECT path FROM files WHERE doc=? ORDER BY path", (doc,)).fetchall()
        for row in paths:
            try:
                data = self.pdf_bytes(row["path"])
            except (OSError, ValueError):
                continue
            if hashlib.sha256(data).hexdigest() == doc:
                return row["path"], data
        raise KeyError("Original no disponible")

    def render(self, doc, page, dpi):
        _, data = self.original(doc)
        with PDF_LOCK, pymupdf.open(stream=data, filetype="pdf") as pdf:
            if not 1 <= page <= len(pdf):
                raise KeyError("Página fuera de rango")
            source = pdf[page - 1]
            w, h = source.rect.width, source.rect.height
            if w <= 0 or h <= 0:
                raise ValueError("Página inválida")
            scale = min(dpi / 72, 3200 / max(w, h), math.sqrt(4_000_000 / (w * h)))
            return source.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False).tobytes("png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Indexar PDF locales; por defecto el corte de dos PDF más pequeños.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--limit", type=int, default=2)
    group.add_argument("--all", action="store_true")
    args = parser.parse_args()
    result = Corpus.configured().index(None if args.all else args.limit)
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["indexed"] + result["reused"] else 1)
