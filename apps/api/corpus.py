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


def asks_definition(question):
    return bool(re.search(r"\b(qué es|qué significa|cómo se define)\b", question.casefold()))


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
        tokens = terms(request.query)[:18]
        if not tokens:
            return []
        ranking_terms = tokens
        if asks_definition(request.query):
            ranking_terms = tokens + ["refiere", "define", "consiste"]
        expression = " OR ".join(f'"{t}"' for t in ranking_terms)
        with closing(self.connect()) as db:
            rows = db.execute("""
                SELECT doc, page, fragment, body FROM chunks WHERE chunks MATCH ?
                ORDER BY bm25(chunks) ASC, doc, page, fragment LIMIT ?
            """, (expression, request.top_k * 4)).fetchall()
        # Rechazar coincidencias débiles antes de presentarlas como evidencia.
        required = math.ceil(len(tokens) * 0.8)
        required_numbers = {t for t in tokens if any(c.isdigit() for c in t)}
        matches = []
        for row in rows:
            common = set(tokens).intersection(terms(row["body"]))
            if len(common) >= required and required_numbers <= common:
                matches.append(SourceRef(doc_id=row["doc"], pdf_page=row["page"], fragment=row["fragment"]))
            if len(matches) == request.top_k:
                break
        return matches

    def read_source(self, ref: SourceRef):
        with closing(self.connect()) as db:
            row = db.execute("""
                SELECT body
                FROM chunks WHERE doc=? AND page=? AND fragment=?
            """, (ref.doc_id, ref.pdf_page, ref.fragment)).fetchone()
        if not row:
            raise KeyError("Evidencia desconocida")
        name, _ = self.original(ref.doc_id)
        return Citation(doc_id=ref.doc_id, filename=name, pdf_page=ref.pdf_page,
                        evidence_id=f"{ref.doc_id}:{ref.pdf_page}:{ref.fragment}", snippet=row["body"])

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
