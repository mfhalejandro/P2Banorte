import asyncio
from contextlib import closing
from dataclasses import replace
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from apps.api.corpus import Citation, Corpus
from apps.api.finance import Abstain, Operand, Unit, calculate, decimal_from_source, display
from apps.api.financial_agent import LocalToolDouble, ToolCall, parse_intent
from apps.api.main import create_app
from fixtures import example, report

DIFF = "Compara la utilidad neta de Grupo Faro entre 3T24 y 3T25"
CHANGE = "Calcula la variación porcentual de la utilidad neta de Grupo Faro entre 3T24 y 3T25"


@pytest.fixture
def corpus(tmp_path):
    folder = tmp_path / "reports"
    example(folder)
    index = Corpus(folder, tmp_path / "state")
    assert index.index()["unique"] == 2
    return index


def ask(client, question=DIFF):
    response = client.post("/api/chat", json={"message": question})
    assert response.status_code == 200, response.text
    return response.json()


def test_financial_flow_uses_existing_index_and_original_pages(corpus, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "financial-local")
    with closing(corpus.connect()) as db:
        baseline = list(db.iterdump())
    with TestClient(create_app(Corpus(corpus.data, corpus.db.parent))) as api:
        total = ask(api)
        assert total["status"] == "answered"
        assert "12.29 millones de mxn" in total["answer"].lower()
        assert total["provider_mode"] == "financiero local (doble)"
        assert total["tools_used"].count("search_corpus") == 2
        assert total["tools_used"][-1] == "financial_calculator"
        cite_a, cite_b = total["citations"]
        assert cite_a["filename"] == "A-base.pdf" and "111.11" in cite_a["snippet"]
        assert cite_b["filename"] == "B-consultado.pdf" and "123.40" in cite_b["snippet"]
        for cite in total["citations"]:
            assert cite["pdf_page"] == 2
            image = api.get(f'/api/documents/{cite["doc_id"]}/pages/2/image')
            assert image.content == corpus.render(cite["doc_id"], 2, 125)
        assert "11.06 %" in ask(api, CHANGE)["answer"]
        mixed = ask(api, DIFF.replace("3T25", "9M25"))
        assert mixed["status"] == "abstained" and "distinto tipo" in mixed["answer"]
        assert len(mixed["citations"]) == 2
        assert "inspect_page_visual" in ask(api, DIFF + " e inspecciona la página")["tools_used"]
    with closing(corpus.connect()) as db:
        assert list(db.iterdump()) == baseline


@pytest.mark.parametrize("case,reason", [
    ("currency", "monedas"),
    ("basis", "cambio de perímetro"),
    ("ambiguous", "columna inequívoca"),
    ("wrong_entity", "entidad"),
    ("zero", "base mayor que cero"),
])
def test_comparison_abstains_with_reason(corpus, case, reason):
    base, current = corpus.data / "A-base.pdf", corpus.data / "B-consultado.pdf"
    if case == "zero":
        report(base, ("3T24", "9M24"), ("0", "280.05"))
    else:
        options = {
            "currency": {"unit": "millones USD"},
            "basis": {"note": "Nota: reexpresión por cambio de perímetro."},
            "ambiguous": {"duplicate_header": True},
            "wrong_entity": {"entity": "Grupo Norte"},
        }[case]
        report(current, ("3T25", "9M25"), ("123.40", "310.10"), **options)
    corpus.index()
    with TestClient(create_app(corpus, financial_provider=LocalToolDouble())) as api:
        result = ask(api, CHANGE)
    assert result["status"] == "abstained"
    assert reason in result["answer"]


def test_missing_period(corpus):
    with TestClient(create_app(corpus, financial_provider=LocalToolDouble())) as api:
        result = ask(api, DIFF.replace("3T25", "4T25"))
    assert result["status"] == "abstained" and "4T25" in result["answer"]


class ScriptedFailure(LocalToolDouble):
    def __init__(self, scenario):
        self.scenario = scenario

    async def propose(self, intent, trace):
        if self.scenario == "invalid":
            return {"name": "not_a_tool", "arguments": {}}
        if self.scenario == "offline":
            raise ConnectionError()
        if self.scenario == "slow":
            await asyncio.sleep(2)
        if self.scenario == "fabricated":
            return ToolCall(name="financial_calculator", arguments={
                "operation": intent.operation, "base": "inventado", "current": "también inventado",
            })
        return ToolCall(name="list_documents", arguments={})


@pytest.mark.parametrize("scenario", ["invalid", "offline", "slow", "loop", "fabricated"])
def test_tool_protocol_fails_closed(corpus, scenario):
    with TestClient(create_app(corpus, financial_provider=ScriptedFailure(scenario))) as api:
        api.app.state.agent.max_calls = 2
        api.app.state.agent.timeout = 0.3
        response = api.post("/api/chat", json={"message": DIFF})
    if scenario == "fabricated":
        assert response.json()["status"] == "abstained" and response.json()["citations"] == []
    else:
        assert response.status_code == 503


def test_decimal_operations_and_scale():
    intent = parse_intent(DIFF)
    citation = Citation(doc_id="a", filename="A.pdf", pdf_page=2, evidence_id="a:2", snippet="")
    millions = Unit("moneda", "MXN", Decimal("1000000"), "millones MXN")
    thousands = replace(millions, scale=Decimal("1000"), label="miles MXN")
    base = Operand(citation, intent.metric, "Grupo Faro", intent.base, thousands,
                   "consolidado", "111110", Decimal("111110"), additive=True)
    current = replace(base, period=intent.current, unit=millions, original="123.40", value=Decimal("123.40"))
    assert calculate("difference", base, current)[0] == Decimal("12.29")
    assert display(calculate("percent_change", base, current)[0]) == "11.06"
    assert display(calculate("ratio", base, current)[0]) == "1.11"
    assert calculate("sum", base, current)[0] == Decimal("234.51")
    assert display(Decimal("3.125")) == "3.12"
    assert display(Decimal("3.135")) == "3.14"
    rate = Unit("tasa", None, Decimal(1), "%")
    assert calculate("difference", replace(base, unit=rate, value=Decimal("11")),
                     replace(current, unit=rate, value=Decimal("12.5")))[:2] == (
                         Decimal("1.5"), "puntos porcentuales")
    with pytest.raises(Abstain):
        calculate("sum", base, replace(current, period=base.period))
    with pytest.raises(Abstain):
        calculate("ratio", replace(base, value=Decimal(0)), current)
    with pytest.raises(Abstain):
        calculate("percent_change", replace(base, value=Decimal(-1)), current)
    for bad in ("NaN", "Infinity", "4,123", "13 14"):
        with pytest.raises(Abstain):
            decimal_from_source(bad)
    assert decimal_from_source("(1,234.50)") == Decimal("-1234.50")
    assert decimal_from_source("(1.5%)") == Decimal("-1.5")


def test_dynamic_expansion_and_aliases(corpus, tmp_path):
    source = corpus.data / "A-base.pdf"
    (corpus.data / "duplicado.pdf").write_bytes(source.read_bytes())
    (corpus.data / "roto.pdf").write_bytes(b"corrupto")
    first = corpus.index()
    assert first["unique"] == 2 and first["reused"] == 3 and len(first["failed"]) == 1
    assert list(first["aliases"].values()) == [["A-base.pdf", "duplicado.pdf"]]
    next_folder = tmp_path / "other"
    next_folder.mkdir()
    report(next_folder / "sin-nombre-conocido.pdf", ("1T25", "2T25"), ("4,018", "4,238"),
           unit="millones de pesos")
    other = Corpus(next_folder, tmp_path / "other-state")
    result = other.index()
    assert result["unique"] == 1 and result["indexed"] == 1
    assert other.catalog()[0]["doc_id"] not in {entry["doc_id"] for entry in corpus.catalog()}
    with TestClient(create_app(other, financial_provider=LocalToolDouble())) as api:
        result = ask(api, "Compara utilidad neta de Grupo Faro entre 1T25 y 2T25")
    assert result["status"] == "answered" and "220 millones de pesos" in result["answer"]
    assert all(c["filename"] == "sin-nombre-conocido.pdf" for c in result["citations"])


def test_interrupted_expansion_retains_index(corpus, monkeypatch):
    expected = corpus.catalog()
    report(corpus.data / "new.pdf", ("1T25", "2T25"), ("3.00", "4.00"))
    original = corpus.pdf_bytes

    def interrupted(relative):
        if relative == "new.pdf":
            raise KeyboardInterrupt
        return original(relative)

    monkeypatch.setattr(corpus, "pdf_bytes", interrupted)
    with pytest.raises(KeyboardInterrupt):
        corpus.index()
    assert corpus.catalog() == expected


def test_existing_index_can_open_during_ingestion(corpus):
    expected = corpus.catalog()
    with closing(corpus.connect()) as writer:
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("DELETE FROM files")
        assert Corpus(corpus.data, corpus.db.parent).catalog() == expected
        writer.rollback()
