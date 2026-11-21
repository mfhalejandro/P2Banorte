import json
import sqlite3
from decimal import Decimal

import httpx
import pytest
from fastapi.testclient import TestClient

from apps.api.deepseek_config import SpendLedger, USD_NANO
from apps.api.deepseek_fixture import HYBRID_QUESTIONS
from apps.api.financial_agent import parse_intent
from apps.api.hybrid_agent import document_needs, interpret_query, split_financial_operations
from apps.api.hybrid_planner import question_hash
from apps.api.main import create_app


def test_ordered_operations_keep_separate_periods_and_units():
    parts = split_financial_operations(
        "Dos mediciones: primero, el crecimiento porcentual de la utilidad neta de Grupo Faro de 6M23 a 6M24; "
        "segundo, cuántos puntos porcentuales avanzó el ROA de 1T24 a 2T24."
    )
    intents = [parse_intent(part) for part in parts]
    assert [(i.metric, i.entity, i.base.label, i.current.label, i.operation) for i in intents] == [
        ("utilidad neta", "Grupo Faro", "6M23", "6M24", "percent_change"),
        ("ROA", "Grupo Faro", "1T24", "2T24", "difference"),
    ]
    assert [i.percentage_points for i in intents] == [False, True]
    assert split_financial_operations("Calcula el cambio de utilidad neta entre 6M23 y 6M24 "
                                     "y calcula el cambio del ROE entre 1T24 y 2T24. Usa GBP.") is None


def test_punctuated_composition_keeps_operations_and_calendar_separate():
    parts = split_financial_operations(
        "Indica la diferencia del ROE de Grupo Faro entre 1T24 y 3T24 y, por otra parte, "
        "calcula la variación de utilidad neta de 6M23 a 6M24."
    )
    first, second = map(parse_intent, parts)
    assert (first.operation, first.base.label, first.current.label) == ("difference", "1T24", "3T24")
    assert (second.operation, second.base.label, second.current.label) == ("percent_change", "6M23", "6M24")


def test_documentary_presentation_is_separated_from_evidence_facets():
    methods, reports = document_needs(
        "Presenta las metodologías de gestión de liquidez de la Tenedora y describe, por separado, "
        "a quién se envían los informes trimestrales."
    )
    assert ("pruebas",) in methods.facets
    assert ("trimestral",) in reports.facets and ("mensual",) not in reports.facets
    assert {"presenta", "describe", "separado"}.isdisjoint(methods.permitted + reports.permitted)


def test_uninterpreted_request_cannot_disappear_from_coverage(tmp_path, monkeypatch):
    from apps.api.deepseek_fixture import synthetic_corpus

    question = "¿Qué es el margen operativo? Por separado, explica qué política entrará en vigor en 2043."
    interpretation = interpret_query(question)
    assert interpretation.status == "partial"
    assert interpretation.unresolved == (1,)
    are_valid = [part.span.text == question[part.span.start:part.span.end] for part in interpretation.parts]
    assert all(are_valid)
    monkeypatch.setenv("LLM_PROVIDER", "hybrid-experimental")
    monkeypatch.setenv("HYBRID_DEEPSEEK_SCOPE", "blocked")
    with TestClient(create_app(synthetic_corpus(str(tmp_path)))) as client:
        response = client.post("/api/chat", json={"message": question})
    assert response.status_code == 200
    assert response.headers["x-hybrid-requested"] == "2"
    assert response.headers["x-hybrid-evidenced"] == "1"
    assert response.headers["x-hybrid-uninterpreted"] == "1"
    assert response.headers["x-hybrid-coverage"] == "partial"
    assert response.headers["x-hybrid-decision"] != "complete"
    assert "pendiente" in response.json()["answer"].lower()
    assert {citation["pdf_page"] for citation in response.json()["citations"]} == {1}


def test_independent_operations_keep_clause_local_currency():
    question = (
        "Calcula el cambio del ROA de Grupo Faro entre 1T24 y 2T24. "
        "Después calcula la diferencia de utilidad neta de Grupo Faro entre 6M23 y 6M24 en millones de MXN."
    )
    first, second = interpret_query(question).parts
    assert first.financial.metric == "ROA" and first.financial.output_currency is None
    assert second.financial.metric == "utilidad neta"
    assert (second.financial.base.label, second.financial.current.label) == ("6M23", "6M24")
    assert (second.financial.output_currency, second.financial.output_scale) == ("MXN", "millones")


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


@pytest.mark.parametrize("currency", [
    "francos suizos", "CHF", "chf", "dólares canadienses", "GBP", "libras esterlinas",
    "pesos argentinos", "yenes", "moneda: ARS", "dólares de Hong Kong", "pesos de Chile",
    "dólares (canadienses)",
])
def test_currency_request_stops_before_tools(currency, monkeypatch, tmp_path):
    from apps.api.deepseek_fixture import synthetic_corpus

    root = tmp_path / "fixture"
    root.mkdir()
    corpus = synthetic_corpus(str(root))
    question = f"Compara la utilidad neta de Grupo Faro entre 3T24 y 3T25. Usa exclusivamente {currency}."
    for provider in ("financial-local", "hybrid-experimental"):
        monkeypatch.setenv("LLM_PROVIDER", provider)
        monkeypatch.setenv("HYBRID_DEEPSEEK_SCOPE", "blocked")
        with TestClient(create_app(corpus)) as client:
            response = client.post("/api/chat", json={"message": question})
            value = response.json()
            assert response.status_code == 200 and value["status"] == "abstained"
            assert "moneda" in value["answer"]
            assert "12.29" not in value["answer"]
            assert value["citations"] == value["tools_used"] == []
            assert response.headers.get("x-p2-deepseek-calls", "0") == "0"


def test_default_mode_cannot_inherit_external_provider(monkeypatch, tmp_path):
    from apps.api.deepseek_config import runtime_env

    envfile = tmp_path / "mode.env"
    envfile.write_text("LLM_PROVIDER=deepseek\nDEEPSEEK_ALLOW_REAL_DATA=true\n")
    envfile.chmod(0o600)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("P2BANORTE_ENV_FILE", str(envfile))
    assert "LLM_PROVIDER" not in runtime_env()


def test_report_year_is_a_source_constraint_and_future_is_protected():
    from apps.api.hybrid_agent import document_needs, report_scope

    question = "Según los estados financieros de 2025, ¿cómo se define el coeficiente de cobertura de liquidez de la Tenedora?"
    need, = document_needs(question)
    assert need.year == 2025 and need.kind == "definition"
    assert report_scope(need, "EEFF 2025 Grupo.pdf")
    assert not report_scope(need, "EEFF 2024 Grupo.pdf")
    assert not report_scope(need, "Anexo anual 2025 Grupo.pdf")
    assert not document_needs("¿Qué reglas de liquidez adoptará la Tenedora en 2098?")


def test_relative_year_requires_an_explicit_anchor():
    from apps.api.financial_agent import normalize_periods

    assert normalize_periods("del 3T23 al tercer trimestre del año siguiente") == "del 3T23 al 3T24"
    assert normalize_periods("tercer trimestre del año siguiente") == "tercer trimestre del año siguiente"


def test_plan_cannot_rewrite_financial_constraints(sandbox, monkeypatch):
    monkeypatch.setenv("HYBRID_DEEPSEEK_SCOPE", "synthetic")
    def bad_plan(body):
        slot, = body["pendientes"]
        interpretation = slot["restricciones"] | {"currency": "CHF"}
        return wire_reply({"subquestions": [{"slot": slot["slot"], "search_terms": [],
                                            "interpretation": interpretation}]})
    fixture = PlannerFixture(bad_plan)
    with TestClient(create_app(deepseek_transport=httpx.MockTransport(fixture.send))) as client:
        result = query(client, "metrics")
        assert result.headers["x-hybrid-decision"] == "invalid-plan"
        assert result.headers["x-p2-deepseek-calls"] == "1"
        assert "12.29 millones de mxn" in result.json()["answer"]
        assert "pendiente verificar roe" in result.json()["answer"]


def test_production_planner_never_loads_external_settings_or_transport(sandbox, monkeypatch, tmp_path, caplog):
    from apps.api.deepseek_fixture import synthetic_corpus

    def forbidden(*args, **kwargs):
        pytest.fail("El modo determinista no debe configurar ni llamar al proveedor externo.")

    root = tmp_path / "deterministic-corpus"
    root.mkdir()
    corpus = synthetic_corpus(str(root))
    envfile = tmp_path / "provider.env"
    with envfile.open("a") as stream:
        stream.write("LLM_PROVIDER=deepseek\nHYBRID_DEEPSEEK_SCOPE=authorized\n")
    monkeypatch.setattr("apps.api.main.planner_settings", forbidden)
    with TestClient(create_app(corpus, deepseek_transport=httpx.MockTransport(forbidden))) as client:
        health = client.get("/api/health").json()
        assert health["planner"] == "deterministic"
        assert health["external_data_scope"] == "blocked"
        assert health["external_provider_ready"] is False
        with caplog.at_level("INFO", logger="uvicorn.error"):
            rescued = query(client, "sections")
        assert rescued.headers["x-hybrid-rescue-activated"] == "1"
        assert rescued.headers["x-hybrid-sections-verified"] == "0,1"
        assert rescued.headers["x-hybrid-sections-attempted"] == "0:definition,1:passage"
        assert rescued.headers["x-hybrid-planner"] == "deterministic"
        assert int(rescued.headers["x-hybrid-rescue-ms"]) >= 0
        assert "activated=1 attempted=0:definition,1:passage verified=0,1" in caplog.text
        assert "reserva de efectivo" in rescued.json()["answer"]
        assert HYBRID_QUESTIONS["sections"] not in caplog.text
        for name in ("complete", "invalid", "entity_metric"):
            assert query(client, name).headers["x-hybrid-rescue-activated"] == "0"
        for key in ("x-p2-deepseek-calls", "x-p2-deepseek-input", "x-p2-deepseek-output", "x-p2-deepseek-usd-upper"):
            assert Decimal(rescued.headers[key]) == 0
    with sqlite3.connect(sandbox) as db:
        assert db.execute("SELECT nano FROM spend").fetchone()[0] == 0


@pytest.mark.parametrize("failure", ["timeout", "invalid-schema"])
def test_deterministic_rescue_preserves_calculation_on_failure(monkeypatch, tmp_path, failure):
    from apps.api.deepseek_fixture import synthetic_corpus

    root = tmp_path / "fallback-corpus"
    root.mkdir()
    corpus = synthetic_corpus(str(root))

    async def broken_plan(self, question, slots, totals):
        if failure == "timeout":
            raise TimeoutError()
        return {"subquestions": [{"slot": -1, "search_terms": []}]}

    monkeypatch.setenv("LLM_PROVIDER", "hybrid-experimental")
    monkeypatch.setenv("HYBRID_DEEPSEEK_SCOPE", "blocked")
    monkeypatch.setattr("apps.api.hybrid_planner.DeterministicPlanner.plan", broken_plan)
    with TestClient(create_app(corpus)) as client:
        response = query(client, "metrics")
        assert response.headers["x-hybrid-decision"] == ("fallback" if failure == "timeout" else "invalid-plan")
        assert response.headers["x-hybrid-rescue-activated"] == "1"
        assert response.headers["x-hybrid-sections-verified"] == "-"
        assert response.headers["x-p2-deepseek-calls"] == "0"
        assert "12.29 millones de mxn" in response.json()["answer"]
        assert "pendiente verificar roe" in response.json()["answer"]
        assert len(response.json()["citations"]) == 2


def test_calendar_exclusion_does_not_cite_an_unrelated_basis_warning():
    import asyncio

    from apps.api.agent import ChatResponse
    from apps.api.hybrid_agent import HybridAgent, RequestBudget
    from apps.api.hybrid_planner import DeterministicPlanner
    from types import SimpleNamespace

    async def verify():
        base = ChatResponse(
            request_id="fixture", provider_mode="financiero local (doble)", status="abstained",
            answer="No puedo calcular. Falta base común por cambio de perímetro.",
            citations=[], warnings=["Cambio de perímetro."], tools_used=["read_source"],
        )
        agent = HybridAgent(SimpleNamespace(corpus=None), None, DeterministicPlanner())
        budget = RequestBudget(asyncio.get_running_loop().time() + 15)
        reply, stage = await agent.finance(
            "¿Qué proporción representa la utilidad neta de 4T25 respecto de 9M25?", base, budget, None
        )
        assert stage == "local-diagnostic"
        assert "4T25 no está incluido en el acumulado solicitado 9M25" in reply.answer
        assert reply.status == "abstained" and not reply.citations and not reply.warnings
        assert budget.rescue_started is None

    asyncio.run(verify())


def test_financial_presentation_is_traced_without_a_second_operation():
    question = "Calcula la diferencia de ROE de Grupo Faro de 1T24 a 2T24. Indica las dos tasas originales."
    part, = interpret_query(question).parts
    assert part.financial and part.status == "valid"
    assert part.presentation == ("Indica las dos tasas originales.",)
    assert part.span.text == question


@pytest.mark.parametrize("financial_first", [True, False])
def test_mixed_parts_have_independent_citations_and_coverage(monkeypatch, tmp_path, financial_first):
    from apps.api.deepseek_fixture import synthetic_corpus

    financial = "Calcula la diferencia de utilidad neta de Grupo Faro entre 3T24 y 3T25"
    documentary = "Explica qué es el margen operativo"
    parts = (financial, documentary) if financial_first else (documentary, financial)
    question = ". ".join(parts) + "."
    corpus = synthetic_corpus(str(tmp_path))
    monkeypatch.setenv("LLM_PROVIDER", "hybrid-experimental")
    monkeypatch.setenv("HYBRID_DEEPSEEK_SCOPE", "blocked")
    with TestClient(create_app(corpus)) as client:
        response = client.post("/api/chat", json={"message": question})
    assert response.status_code == 200
    assert response.headers["x-hybrid-requested"] == "2"
    assert response.headers["x-hybrid-evidenced"] == "2"
    assert response.headers["x-hybrid-coverage"] == "complete"
    assert "12.29 millones de mxn" in response.json()["answer"]
    assert {cite["pdf_page"] for cite in response.json()["citations"]} == {1, 3}
    assert response.headers["x-p2-deepseek-calls"] == "0"


def test_growth_reference_keeps_its_operands_with_the_absolute_result():
    question = (
        "¿Cuántos millones de pesos adicionales obtuvo Grupo Faro en utilidad neta de 9M23 a 9M24 "
        "y qué variación relativa supone?"
    )
    part, = interpret_query(question).parts
    assert part.financial.operation == "percent_change" and part.financial.additional_difference
    assert (part.financial.base.label, part.financial.current.label) == ("9M23", "9M24")


def test_disclosure_intent_does_not_require_named_recipients():
    question = (
        "Menciona la política de revelación del riesgo de liquidez de la Tenedora. "
        "A continuación enumera las metodologías de gestión de liquidez."
    )
    policy, management = interpret_query(question).parts
    assert policy.documentary.kind == "list" and "revelacion" in policy.documentary.facets[0]
    assert management.documentary.kind == "passage"
    assert ("pruebas",) in management.documentary.facets
