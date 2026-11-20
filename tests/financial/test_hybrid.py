import json
import sqlite3
from decimal import Decimal

import httpx
import pytest
from fastapi.testclient import TestClient

from apps.api.deepseek_config import SpendLedger, USD_NANO
from apps.api.deepseek_fixture import HYBRID_QUESTIONS
from apps.api.hybrid_planner import question_hash
from apps.api.main import create_app


@pytest.fixture
def sandbox(monkeypatch, tmp_path):
    for flag in ("HYBRID_DEEPSEEK_SCOPE", "HYBRID_DEEPSEEK_ALLOWLIST"):
        monkeypatch.delenv(flag, raising=False)
    envfile = tmp_path / "provider.env"
    envfile.write_text("DEEPSEEK_API_KEY=fixture-key\nDEEPSEEK_ALLOW_REAL_DATA=true\n")
    envfile.chmod(0o600)
    ledger = tmp_path / "budget.sqlite3"
    SpendLedger(ledger, Decimal("0.01"))
    monkeypatch.setenv("LLM_PROVIDER", "hybrid-experimental")
    monkeypatch.setenv("P2BANORTE_ENV_FILE", str(envfile))
    monkeypatch.setenv("DEEPSEEK_BUDGET_FILE", str(ledger))
    monkeypatch.setenv("HYBRID_DEEPSEEK_BUDGET_USD", "0.01")
    return ledger


def wire_reply(content, *, calls=None):
    return httpx.Response(200, json={
        "choices": [{
            "finish_reason": "tool_calls" if calls else "stop",
            "message": {"role": "assistant", "content": json.dumps(content), "tool_calls": calls or []},
        }],
        "usage": {"prompt_tokens": 77, "completion_tokens": 20},
    })


class PlannerFixture:
    def __init__(self, respond=None):
        self.requests = []
        self.respond = respond

    async def send(self, request):
        payload = json.loads(request.content)
        self.requests.append(payload)
        assert str(request.url) == "https://api.deepseek.com/chat/completions"
        assert payload["thinking"] == {"type": "disabled"}
        assert "tools" not in payload and "tool_choice" not in payload
        assert payload["max_tokens"] == 256
        assert len(payload["messages"]) == 2
        body = json.loads(payload["messages"][1]["content"])
        assert set(body) == {"pregunta", "pendientes"}
        assert not any(value in str(payload) for value in ("revelar_secretos", ".pdf", "111.11", "123.40"))
        if self.respond:
            return self.respond(body)
        return wire_reply({"subquestions": [{"slot": slot["slot"], "search_terms": []}
                                           for slot in body["pendientes"]]})


def query(client, name):
    result = client.post("/api/chat", json={"message": HYBRID_QUESTIONS[name]})
    assert result.status_code == 200
    assert int(result.headers["x-hybrid-tools"]) <= 24
    assert int(result.headers["x-hybrid-total-ms"]) < 15000
    return result


def test_local_and_abstentions_bypass_provider(sandbox, monkeypatch):
    monkeypatch.setenv("HYBRID_DEEPSEEK_SCOPE", "synthetic")
    fixture = PlannerFixture()
    with TestClient(create_app(deepseek_transport=httpx.MockTransport(fixture.send))) as client:
        assert client.get("/api/health").json()["external_data_scope"] == "synthetic"
        for name, phrase in (("complete", "= 12.29 millones de mxn"), ("invalid", "no es aditiva"),
                             ("entity_metric", "distinto tipo o duración")):
            response = query(client, name)
            assert phrase in response.json()["answer"]
            assert response.headers["x-p2-deepseek-calls"] == "0"
        arbitrary = client.post("/api/chat", json={"message": "¿A qué se refiere alguien cuando habla de riesgo de crédito?"})
        assert arbitrary.status_code == 200 and arbitrary.headers["x-p2-deepseek-calls"] == "0"
    assert not fixture.requests


@pytest.mark.parametrize(("name", "proof", "pages"), [
    ("indirect", ("proporción de los ingresos",), {1}),
    ("definition", ("proporción de los ingresos",), {1}),
    ("sections", ("proporción de los ingresos", "reserva de efectivo"), {1, 2}),
    ("metrics", ("12.29 millones de mxn", "1.5 puntos porcentuales"), {3}),
])
def test_rescue_from_local_sources(sandbox, monkeypatch, name, proof, pages):
    monkeypatch.setenv("HYBRID_DEEPSEEK_SCOPE", "synthetic")
    fixture = PlannerFixture()
    with TestClient(create_app(deepseek_transport=httpx.MockTransport(fixture.send))) as client:
        response = query(client, name)
        value = response.json()
        for fragment in proof:
            assert fragment in value["answer"]
        assert response.headers["x-hybrid-decision"] == "rescued"
        assert response.headers["x-p2-deepseek-calls"] == "1"
        assert {cite["pdf_page"] for cite in value["citations"]} == pages
        for cite in value["citations"]:
            png = client.get(f"/api/documents/{cite['doc_id']}/pages/{cite['pdf_page']}/image")
            assert png.status_code == 200 and png.content.startswith(b"\x89PNG")
        for _ in range(2):
            assert query(client, name).headers["x-p2-deepseek-calls"] == "0"
        assert len(fixture.requests) == 1
    with sqlite3.connect(sandbox) as db:
        assert db.execute("SELECT nano FROM spend").fetchone()[0] == 77 * 300 + 20 * 1200


@pytest.mark.parametrize("failure", ["invalid-schema", "invalid-slot", "invalid-terms", "tool", "timeout", "budget"])
def test_preserves_financial_result_on_failed_rescue(sandbox, monkeypatch, failure):
    monkeypatch.setenv("HYBRID_DEEPSEEK_SCOPE", "synthetic")
    if failure == "budget":
        with sqlite3.connect(sandbox) as db:
            db.execute("UPDATE spend SET nano=?", (int(Decimal("0.01") * USD_NANO),))
    def bad_plan(_):
        if failure == "timeout":
            raise httpx.ReadTimeout("fixture timeout")
        if failure == "tool":
            return wire_reply(None, calls=[{"id": "fixture", "type": "function",
                                           "function": {"name": "read_source", "arguments": "{}"}}])
        if failure == "invalid-slot":
            return wire_reply({"subquestions": [{"slot": 1, "search_terms": []}]})
        if failure == "invalid-terms":
            return wire_reply({"subquestions": [{"slot": 0, "search_terms": ["USD"]}]})
        return wire_reply({"answer": "made up", "subquestions": []})
    fixture = PlannerFixture(bad_plan)
    with TestClient(create_app(deepseek_transport=httpx.MockTransport(fixture.send))) as client:
        response = query(client, "metrics")
        value = response.json()
        assert "= 12.29 millones de mxn" in value["answer"]
        assert "pendiente verificar roe" in value["answer"]
        assert response.headers["x-hybrid-decision"] in {"fallback", "invalid-plan"}
        assert len(value["citations"]) == 2
        assert len(fixture.requests) == (0 if failure == "budget" else 1)


def test_rejects_nonpertinent_evidence_and_keeps_partial(sandbox, monkeypatch):
    monkeypatch.setenv("HYBRID_DEEPSEEK_SCOPE", "synthetic")
    fixture = PlannerFixture()
    with TestClient(create_app(deepseek_transport=httpx.MockTransport(fixture.send))) as client:
        partial = query(client, "partial")
        assert partial.headers["x-hybrid-decision"] == "partial-rescue"
        value = partial.json()
        assert "Respuesta parcial" in value["answer"]
        assert "reserva de efectivo" not in value["answer"]
        assert all(cite["pdf_page"] == 1 for cite in value["citations"])
        assert query(client, "restrictions").headers["x-p2-deepseek-calls"] == "0"


def test_global_flag_does_not_authorize_hybrid_and_allowlist_is_exact(sandbox, monkeypatch, tmp_path):
    from apps.api.deepseek_fixture import synthetic_corpus

    fixture = PlannerFixture()
    root = tmp_path / "local-corpus"
    root.mkdir()
    corpus = synthetic_corpus(str(root))
    with TestClient(create_app(corpus, deepseek_transport=httpx.MockTransport(fixture.send))) as client:
        assert client.get("/api/health").json()["external_data_scope"] == "blocked"
        assert query(client, "indirect").headers["x-p2-deepseek-calls"] == "0"
    monkeypatch.setenv("HYBRID_DEEPSEEK_SCOPE", "authorized")
    path = tmp_path / "authorized.txt"
    path.write_text(question_hash(HYBRID_QUESTIONS["indirect"]) + "\n")
    path.chmod(0o600)
    monkeypatch.setenv("HYBRID_DEEPSEEK_ALLOWLIST", str(path))
    with TestClient(create_app(corpus, deepseek_transport=httpx.MockTransport(fixture.send))) as client:
        assert client.get("/api/health").json()["external_data_scope"] == "authorized"
        assert query(client, "sections").headers["x-p2-deepseek-calls"] == "0"
        assert query(client, "indirect").headers["x-p2-deepseek-calls"] == "1"
    assert len(fixture.requests) == 1
