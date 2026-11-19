import asyncio
import hashlib

import pymupdf
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.api.corpus import Corpus, SearchRequest, SourceRef
from apps.api.main import create_app
from fixture_pdf import example_corpus, write_pdf


@pytest.fixture
def corpus(tmp_path):
    folder = example_corpus(tmp_path / "inputs")
    result = Corpus(folder, tmp_path / "state")
    result.index()
    return result


def test_index_idempotent_and_aliases(corpus):
    original = corpus.data / "ensayo.pdf"
    digest = hashlib.sha256(original.read_bytes()).hexdigest()
    (corpus.data / "alias.pdf").write_bytes(original.read_bytes())
    (corpus.data / "malo.pdf").write_bytes(b"invalid")
    report = corpus.index()
    assert (report["indexed"], report["reused"], len(report["failed"])) == (0, 2, 1)
    assert len(corpus.catalog()) == 1
    assert corpus.catalog()[0]["doc_id"] == digest
    with corpus.connect() as db:
        assert db.execute("SELECT count(*) FROM chunks").fetchone()[0] == 3
    assert hashlib.sha256(original.read_bytes()).hexdigest() == digest


def test_search_and_order(corpus):
    ref = corpus.search_corpus(SearchRequest(query="credito"))[0]
    assert ref.pdf_page == 2
    assert "731" in corpus.read_source(ref).snippet
    for query in ['1T-24', 'P/VL', '"', '+++']:
        assert corpus.search_corpus(SearchRequest(query=query)) == []
    write_pdf(corpus.data / "ranking.pdf", ["tesoro tesoro tesoro.", "tesoro.", "tesoro escaso en muchas otras palabras."])
    corpus.index()
    found = corpus.search_corpus(SearchRequest(query="tesoro"))
    with corpus.connect() as db:
        order = db.execute("SELECT page FROM chunks WHERE chunks MATCH ? ORDER BY bm25(chunks), doc, page, fragment",
                           ("tesoro",)).fetchall()
    assert len(found) == 3
    assert [r.pdf_page for r in found] == [r["page"] for r in order]


def test_chat_and_original(corpus):
    with TestClient(create_app(corpus)) as api:
        response = api.post("/api/chat", json={"message": "¿Cuánto asciende la reserva de crédito Faro?"})
        assert response.status_code == 200
        data = response.json()
        assert "731" in data["answer"] and data["provider_mode"] == "extractivo local"
        cite = data["citations"][0]
        assert cite["pdf_page"] == 2 and data["tools_used"][:2] == ["search_corpus", "read_source"]
        url = "/api/documents/" + cite["doc_id"] + "/pages/"
        image = api.get(url + "2/image")
        with pymupdf.open(corpus.data / "ensayo.pdf") as pdf:
            expected = pdf[1].get_pixmap(matrix=pymupdf.Matrix(125 / 72, 125 / 72)).tobytes("png")
        assert image.headers["content-type"] == "image/png" and image.content == expected
        assert api.get(url + "4/image").status_code == 404
        assert api.get(url + "0/image").status_code == 422
        assert api.get("/api/documents/" + "0"*64 + "/pages/1/image").status_code == 404
        assert api.post("/api/chat", json={"message": "  "}).status_code == 422
        assert api.post("/api/chat", json={"message": "Anillos de Saturno"}).json()["status"] == "abstained"


def test_definition_requires_the_right_topic_and_preserves_column(corpus):
    question = {"message": "¿Qué es el riesgo de crédito?"}
    write_pdf(corpus.data / "Otra definición.pdf", [
        "Análisis de riesgo de crédito. Se define el incumplimiento a partir de 90 días de mora.",
    ])
    corpus.index()
    with TestClient(create_app(corpus)) as api:
        result = api.post("/api/chat", json=question).json()
        assert result["status"] == "abstained" and result["citations"] == []

    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((36, 45), "Riesgo de crédito")
        page.insert_text((290, 45), "Indicador de gestión")
        page.insert_text((36, 65), "La pérdida potencial por la falta de pago de un")
        page.insert_text((290, 65), "Mayorista: gestionado a nivel de cartera.")
        page.insert_text((36, 81), "acreditado o contraparte.")
        pdf.save(corpus.data / "Informe a columnas.pdf")
    corpus.index()

    with TestClient(create_app(corpus)) as api:
        result = api.post("/api/chat", json=question).json()
        assert result["status"] == "answered"
        assert result["answer"] == "Riesgo de crédito: La pérdida potencial por la falta de pago de un acreditado o contraparte."
        citation, = result["citations"]
        assert citation["filename"] == "Informe a columnas.pdf" and citation["pdf_page"] == 1
        assert api.get(f'/api/documents/{citation["doc_id"]}/pages/1/image').headers["content-type"] == "image/png"



def test_definition_separates_source_constraint_and_citation_instructions(corpus):
    for issuer in ("Grupo Faro", "Grupo Norte"):
        with pymupdf.open() as document:
            document.new_page().insert_text((35, 100), "El riesgo de crédito es la posibilidad de impago.")
            document.new_page().insert_text((35, 100), f"Publicación de {issuer}.")
            document.save(corpus.data / f"Informe {issuer}.pdf")
    corpus.index()
    with TestClient(create_app(corpus)) as api:
        for wording in ("¿Cómo se define", "¿Qué significa"):
            prompt = (f"{wording} el riesgo de crédito en los informes de Grupo Faro? "
                      "Indica el documento y la página donde figura la definición.")
            row = api.post("/api/chat", json={"message": prompt}).json()
            assert row["status"] == "answered" and "posibilidad de impago" in row["answer"]
            assert row["citations"][0]["filename"] == "Informe Grupo Faro.pdf"
        missing = api.post("/api/chat", json={
            "message": "¿Cómo se define el riesgo de crédito en los informes de Grupo Inventado?"
        }).json()
        assert missing["status"] == "abstained" and not missing["citations"]


def test_explanatory_answers_use_bounded_lists_with_local_context(corpus):
    def policy_pdf(name, heading, item):
        with pymupdf.open() as document:
            page = document.new_page()
            page.insert_text((36, 120), heading)
            page.insert_text((320, 120), "Riesgo de mercado:")
            if item:
                page.insert_text((50, 143), "• " + item)
            page.insert_text((335, 143), "• Insertar un dato ajeno.")
            page.insert_text((540, 787), "150")
            document.save(corpus.data / name)

    policy_pdf("Objetivos.pdf", "Políticas y objetivos generales:", "Emitir un informe de gestión.")
    policy_pdf("Sin respaldo.pdf", "Políticas de liquidez:", None)
    corpus.index()
    question = {"message": "¿Qué políticas de liquidez se mencionan?"}
    with TestClient(create_app(corpus)) as api:
        result = api.post("/api/chat", json=question).json()
        assert result["status"] == "abstained" and result["citations"] == []

    policy_pdf("A.pdf", "Políticas de liquidez de grupo:", "Medir la liquidez todos los días.")
    policy_pdf("B.pdf", "Políticas de liquidez de banca:", "Establecer límites de liquidez.")
    corpus.index()
    with TestClient(create_app(corpus)) as api:
        result = api.post("/api/chat", json=question).json()
        future = api.post("/api/chat", json={"message": "¿Qué políticas de liquidez adoptarán en el año 2035?"}).json()
    assert result["status"] == "answered"
    assert "selección es parcial" in result["answer"]
    assert "150" not in result["answer"] and "dato ajeno" not in result["answer"]
    assert len(result["citations"]) == 2 and result["tools_used"].count("read_source") <= 4
    expected = {"A.pdf": "Medir la liquidez todos los días.", "B.pdf": "Establecer límites de liquidez."}
    for citation in result["citations"]:
        assert citation["pdf_page"] == 1 and citation["snippet"] in result["answer"]
        assert expected[citation["filename"]] in citation["snippet"]
    assert future["status"] == "abstained" and future["citations"] == []


def test_documentary_paraphrases_preserve_topic_entity_and_constraints(corpus):
    for name, heading, policy in (
        ("Tenedora.pdf", "Políticas de riesgo de liquidez de la Tenedora:", "Establecimiento de límites de liquidez."),
        ("Banco.pdf", "Políticas de riesgo de liquidez del banco:", "Revisar la política del banco."),
        ("Tenedora ampliado.pdf", "Políticas de riesgo de liquidez de la Tenedora vigentes:",
         "El establecimiento de límites de liquidez."),
    ):
        with pymupdf.open() as document:
            page = document.new_page()
            page.insert_text((35, 100), heading)
            page.insert_text((50, 122), "• " + policy)
            document.save(corpus.data / name)
    corpus.index()

    topic = "las políticas de riesgo de liquidez de la Tenedora"
    asks = (
        f"¿Cuáles son {topic}? Enumera las políticas identificadas y señala en qué documento y página se encuentra cada una.",
        f"Señala en qué documento y página se encuentra cada una. ¿Cuáles son {topic}?",
        f"Con documento y página para cada política, enumera {topic}.",
        f"Enumera {topic} e indica el documento y la página de cada una.",
        f"Responde en viñetas; ¿Cuáles son {topic}? Enuméralas.",
    )
    with TestClient(create_app(corpus)) as api:
        for query in asks:
            result = api.post("/api/chat", json={"message": query}).json()
            assert result["status"] == "answered" and result["provider_mode"] == "extractivo local"
            citation, = result["citations"]
            assert citation["filename"] in {"Tenedora.pdf", "Tenedora ampliado.pdf"} and citation["pdf_page"] == 1
            assert "establecimiento de límites de liquidez." in result["answer"].casefold()
            assert "Revisar la política del banco." not in result["answer"]

        for query in (
            f"Cita la fuente y la página. ¿Qué {topic.removeprefix('las ')} se mencionan en el año 2035?",
            f"¿Cuáles son {topic}? Cita el documento y la página 152.",
            f"¿Cuáles son {topic} en dólares? Cita la fuente y la página.",
            "Enumera las políticas identificadas y señala en qué documento y página se encuentra cada una.",
        ):
            result = api.post("/api/chat", json={"message": query}).json()
            assert result["status"] == "abstained" and result["citations"] == []


def test_changed_and_escaped_original(corpus, tmp_path):
    old = corpus.catalog()[0]["doc_id"]
    write_pdf(tmp_path / "nuevo.pdf", ["Página distinta."])
    (corpus.data / "ensayo.pdf").write_bytes((tmp_path / "nuevo.pdf").read_bytes())
    with pytest.raises(KeyError):
        corpus.render(old, 1, 125)
    with pytest.raises(KeyError):
        corpus.read_source(SourceRef(doc_id=old, pdf_page=2, fragment=0))
    (corpus.data / "escape.pdf").symlink_to(tmp_path / "nuevo.pdf")
    assert corpus.index()["selected"] == 1
    assert len(corpus.catalog()) == 1 and corpus.catalog()[0]["doc_id"] != old
    with pytest.raises(ValueError):
        Corpus(corpus.data, corpus.data / "state")
    with pytest.raises(ValidationError):
        SourceRef(doc_id="../escape", pdf_page=1, fragment=0)


class FakeProvider:
    mode = "doble de prueba"

    def __init__(self, outcome):
        self.outcome = outcome

    async def select(self, question, evidence):
        if self.outcome == "caído":
            raise ConnectionError()
        if self.outcome == "lento":
            await asyncio.sleep(2)
        return "fuente-inventada"


@pytest.mark.parametrize("mode,code", [("inventado", 200), ("caído", 503), ("lento", 503)])
def test_provider_limits(corpus, mode, code):
    app = create_app(corpus, FakeProvider(mode))
    with TestClient(app) as api:
        app.state.agent.timeout = 0.3
        response = api.post("/api/chat", json={"message": "reserva Faro"})
        assert response.status_code == code
        if code == 200:
            assert response.json()["citations"] == [] and response.json()["status"] == "abstained"
        app.state.agent.max_calls = 1
        assert api.post("/api/chat", json={"message": "reserva Faro"}).status_code == 503
