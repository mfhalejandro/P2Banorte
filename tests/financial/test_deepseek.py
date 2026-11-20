import json
from collections import deque

import httpx
import pytest
from fastapi.testclient import TestClient

from apps.api.agent import ProviderUnavailable
from apps.api.deepseek_config import SpendLedger, runtime_env
from apps.api.deepseek_fixture import QUESTIONS
from apps.api.main import create_app


@pytest.fixture
def config(tmp_path, monkeypatch):
    settings = {
        "LLM_PROVIDER": "deepseek",
        "P2BANORTE_ENV_FILE": str(tmp_path / "no-file"),
        "DEEPSEEK_API_KEY": "fictitious",  # HTTP interceptado por MockTransport
        "DEEPSEEK_SYNTHETIC": "true",
        "DEEPSEEK_ALLOW_REAL_DATA": "false",
        "DEEPSEEK_BUDGET_FILE": str(tmp_path / "budget.sqlite3"),
    }
    for key, value in settings.items():
        monkeypatch.setenv(key, value)


def tool(identifier, name, **kwargs):
    return {"id": identifier, "type": "function", "function": {"name": name, "arguments": json.dumps(kwargs)}}


def reply(*tools, refs=None):
    content = json.dumps({"references": refs or [], "partial": False}) if not tools else None
    return {"usage": {"prompt_tokens": 300, "completion_tokens": 60},
            "choices": [{"finish_reason": "tool_calls" if tools else "stop",
                         "message": {"role": "assistant", "content": content, "tool_calls": list(tools)}}]}


def backend(*responses):
    capture = []
    queue = deque(responses)

    def handle(request):
        assert str(request.url) == "https://api.deepseek.com/chat/completions"
        assert request.headers["Authorization"] == "Bearer fictitious"
        payload = json.loads(request.content)
        assert payload["model"] == "deepseek-flash" and payload["thinking"] == {"type": "disabled"}
        capture.append(payload)
        message = queue.popleft()
        if message == "timeout":
            raise httpx.ReadTimeout("texto del proveedor")
        if isinstance(message, int):
            return httpx.Response(message, text="texto sensible del proveedor")
        return httpx.Response(200, json=message)

    return capture, TestClient(create_app(deepseek_transport=httpx.MockTransport(handle)))


def ask(api, case):
    return api.post("/api/chat", json={"message": QUESTIONS[case]})


def test_deepseek_calculation_grounded_on_observed_operands(config):
    capture, client = backend(
        reply(tool("a", "search_corpus", query="utilidad neta", period="3T24", other_period="3T25", entity="Grupo Faro"),
              tool("b", "search_corpus", query="utilidad neta", period="3T25", other_period="3T24", entity="Grupo Faro")),
        reply(tool("c", "read_source", reference="S1"), tool("d", "read_source", reference="S2")),
        reply(tool("e", "financial_calculator", operation="difference", base="E1", current="E2")),
        reply(refs=["E3"]),
    )
    with client as api:
        result = ask(api, "difference")
        assert result.status_code == 200
        body = result.json()
        assert body["status"] == "answered" and "12.29 millones de mxn" in body["answer"]
        assert len(body["citations"]) == 2 and body["tools_used"][-1] == "financial_calculator"
        for citation in body["citations"]:
            url = f'/api/documents/{citation["doc_id"]}/pages/{citation["pdf_page"]}/image'
            assert api.get(url).content.startswith(b"\x89PNG")
    assert len(capture) == 4
    for payload in capture[1:]:
        messages = payload["messages"]
        calls = [call["id"] for msg in messages if msg["role"] == "assistant" for call in msg["tool_calls"]]
        assert calls == [msg["tool_call_id"] for msg in messages if msg["role"] == "tool"]
        assert "Faro-informe-ficticio.pdf" not in json.dumps(payload)


def test_private_questions_are_rejected_before_transport(config, monkeypatch, tmp_path):
    capture, client = backend()
    with client as api:
        assert api.post("/api/chat", json={"message": "Dato privado arbitrario"}).status_code == 403
    monkeypatch.setenv("DEEPSEEK_SYNTHETIC", "false")
    monkeypatch.setenv("RAG_DATA_DIR", str(tmp_path / "private"))
    monkeypatch.setenv("RAG_STATE_DIR", str(tmp_path / "private-state"))
    capture2, client2 = backend()
    with client2 as api:
        assert ask(api, "definition").status_code == 403
        assert api.get("/api/health").status_code == 200
    assert not capture and not capture2


@pytest.mark.parametrize("responses", [
    (reply(tool("1", "no_existe")),),
    (reply(refs=["E9"]),),
    (401,), (429,), ("timeout",),
])
def test_invalid_protocol_errors_and_timeout_are_controlled(config, responses):
    capture, client = backend(*responses)
    with client as api:
        response = ask(api, "unknown")
        assert response.status_code == 503
        assert "texto sensible" not in response.text and "fictitious" not in response.text
        assert api.get("/api/documents").status_code == 200
    assert len(capture) == 1


def test_validated_sources_and_untrusted_pdf_instructions(config):
    capture, client = backend(
        reply(tool("1", "search_corpus", query="medida de liquidez de contingencia")),
        reply(tool("2", "read_source", reference="S1")),
        reply(tool("3", "inspect_page_visual", reference="E1")),
        reply(refs=["E1"]),
    )
    with client as api:
        value = ask(api, "injection").json()
        assert value["status"] == "answered" and "reserva de efectivo" in value["answer"]
        assert "revelar_secretos" not in value["answer"] and len(capture) == 4
        assert "revelar_secretos" not in json.dumps(capture[-1])
        assert "inspect_page_visual" in value["tools_used"]


def test_duplicates_unknown_arguments_and_unobserved_operand_are_not_executed(config):
    capture, client = backend(
        reply(tool("1", "financial_calculator", operation="sum", base="E1", current="E2"),
              tool("2", "list_documents", illicit=True)),
        reply(tool("3", "financial_calculator", operation="sum", base="E1", current="E2")),
    )
    with client as api:
        value = ask(api, "invalid").json()
        assert value["status"] == "abstained" and "no es aditiva" in value["answer"]
        assert "dos operandos validados" in value["answer"]
        assert "dejó de avanzar" in value["answer"] and value["citations"] == []
    assert len(capture) == 2


def test_budget_persists_and_env_file_requires_private_mode(tmp_path, monkeypatch):
    path = tmp_path / "budget.sqlite3"
    from decimal import Decimal

    ledger = SpendLedger(path, Decimal("0.01"))
    ledger.reserve(8_000_000)
    with pytest.raises(ProviderUnavailable, match="presupuesto"):
        SpendLedger(path, Decimal("0.01")).reserve(3_000_000)
    ledger.reconcile(8_000_000, 1_000_000)
    SpendLedger(path, Decimal("0.01")).reserve(3_000_000)

    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("P2BANORTE_ENV_FILE", str(tmp_path / "sample.env"))
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    sample = tmp_path / "sample.env"
    sample.write_text('DEEPSEEK_API_KEY="$(false)"\n')
    sample.chmod(0o644)
    with pytest.raises(ProviderUnavailable, match="0600"):
        runtime_env()
    sample.chmod(0o600)
    assert runtime_env()["DEEPSEEK_API_KEY"] == "$(false)"



def test_timeout_then_recovery_without_implicit_retry(config):
    capture, client = backend(
        "timeout",
        reply(tool("a", "search_corpus", query="margen operativo")),
        reply(tool("b", "read_source", reference="S1")),
        reply(refs=["E1"]),
    )
    with client as api:
        assert ask(api, "definition").status_code == 503
        assert len(capture) == 1
        value = ask(api, "definition")
        assert value.status_code == 200 and value.json()["citations"]
        assert value.headers["X-P2-DeepSeek-Calls"] == "3"
    assert len(capture) == 4



def test_malformed_final_keeps_only_verified_blocks_with_warning(config):
    invalid_final = reply()
    invalid_final["choices"][0]["message"]["content"] = '{"unverified":"dato inventado"}'
    capture, client = backend(
        reply(tool("a", "search_corpus", query="margen operativo")),
        reply(tool("b", "read_source", reference="S1")),
        invalid_final,
    )
    with client as api:
        response = ask(api, "definition")
        body = response.json()
        assert response.status_code == 200 and len(capture) == 3 and len(body["citations"]) == 1
        assert "Respuesta parcial" in body["answer"] and "selección final inválida" in body["answer"]
        assert "dato inventado" not in body["answer"]
