import asyncio
from contextlib import closing
from dataclasses import replace
from decimal import Decimal

import pymupdf
import pytest
from fastapi.testclient import TestClient

from apps.api.corpus import Citation, Corpus
from apps.api.finance import Abstain, Operand, Unit, calculate, decimal_from_source, display
from apps.api.financial_agent import LocalToolDouble, ToolCall, parse_intent, requires_financial_tools
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


def test_documentary_suggestions_use_p0_in_financial_mode(corpus, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "financial-local")
    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((55, 55), "El riesgo de crédito es la posibilidad de impago.")
        pdf.save(corpus.data / "Riesgos.pdf")
    assert corpus.index()["unique"] == 3

    with TestClient(create_app(corpus)) as api:
        risk = ask(api, "¿Qué es el riesgo de crédito?")
        assert risk["provider_mode"] == "extractivo local"
        assert risk["status"] == "answered" and "posibilidad de impago" in risk["answer"]
        assert len(risk["citations"]) == 1 and risk["citations"][0]["filename"] == "Riesgos.pdf"

        for question in ("¿Qué políticas de liquidez se mencionan?",
                         "¿Qué es una razón financiera?",
                         "¿Qué políticas de liquidez se mencionan entre 3T24 y 3T25?"):
            result = ask(api, question)
            assert result["provider_mode"] == "extractivo local"
            assert result["tools_used"][0] == "search_corpus"
            assert result["status"] == "abstained" and result["citations"] == []
            assert "evidencia suficiente" in result["answer"]


@pytest.mark.parametrize("question", [
    "Compara la utilidad neta de Grupo Faro en 3T24",
    "Calcula la razón de utilidad neta",
    "¿Cuál fue la variación de la utilidad neta?",
])
def test_incomplete_calculation_requests_a_clarification(corpus, monkeypatch, question):
    monkeypatch.setenv("LLM_PROVIDER", "financial-local")
    with TestClient(create_app(corpus)) as api:
        result = ask(api, question)
    assert result["provider_mode"] == "financiero local (doble)"
    assert result["status"] == "abstained" and "dos periodos distintos" in result["answer"]
    assert result["tools_used"] == result["citations"] == []


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
        ratio = ask(api, DIFF.replace("Compara la", "Calcula la razón de la"))
        assert "1.11 veces" in ratio["answer"] and ratio["tools_used"][-1] == "financial_calculator"
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



@pytest.mark.parametrize(("question", "metric", "periods", "operation", "currency", "scale", "points"), [
    ("Entre 3T24 y 3T25, ¿en qué porcentaje subió la utilidad neta de Grupo Faro? Cita ambas fuentes.",
     "utilidad neta", ("3T24", "3T25"), "percent_change", None, None, False),
    ("Cita la fuente. ¿Cómo cambió el ROE de Grupo Faro entre 3T24 y 3T25? En puntos porcentuales.",
     "ROE", ("3T24", "3T25"), "difference", None, None, True),
    ("Sobre la capitalización de mercado en millones de pesos de Grupo Faro, "
     "¿cuál fue la diferencia entre 1T24 y 2T24?",
     "capitalización de mercado", ("1T24", "2T24"), "difference", "pesos", "millones", False),
])
def test_operation_request_fields(question, metric, periods, operation, currency, scale, points):
    assert requires_financial_tools(question)
    intent = parse_intent(question)
    assert (intent.metric, intent.entity, intent.operation) == (metric, "Grupo Faro", operation)
    assert (intent.base.label, intent.current.label) == periods
    assert (intent.output_currency, intent.output_scale, intent.percentage_points) == (currency, scale, points)


def test_operational_intent_preserves_conceptual_requests_and_constraints(corpus):
    assert not requires_financial_tools("¿Qué significa la variación de una tasa?")
    assert not requires_financial_tools("¿Cómo cambió la política de liquidez de Grupo Faro entre 3T24 y 3T25?")
    with TestClient(create_app(corpus, financial_provider=LocalToolDouble())) as api:
        bad_unit = ask(api, "¿Cómo cambió la utilidad neta de Grupo Faro entre 3T24 y 3T25? En puntos porcentuales.")
        bad_period = ask(api, "¿En qué porcentaje aumentó la utilidad neta de Grupo Faro del 3T24 al 9M25?")
        missing = ask(api, "¿Cómo cambió la utilidad neta de Grupo Faro?")
    assert all(row["status"] == "abstained" for row in (bad_unit, bad_period, missing))
    assert "diferencia entre tasas" in bad_unit["answer"]
    assert "distinto tipo o duración" in bad_period["answer"]
    assert "dos periodos distintos" in missing["answer"] and not missing["tools_used"]


def test_requested_currency_cannot_be_silently_ignored(corpus):
    report(corpus.data / "C-alternativo.pdf", ("3T25", "9M25"), ("123.40", "310.10"),
           note="Hay una reexpresión por cambio de perímetro.")
    corpus.index()
    with TestClient(create_app(corpus, financial_provider=LocalToolDouble())) as api:
        result = ask(api, DIFF + " en dólares")
        assert result["status"] == "abstained"
        assert "moneda solicitada" in result["answer"] and "A − B" not in result["answer"]
        assert not result["warnings"] and "perímetro" not in result["answer"]
        result = ask(api, DIFF + " en millones de MXN")
        assert result["status"] == "answered" and "12.29" in result["answer"]


def test_natural_difference_question_keeps_requested_entity(corpus):
    with TestClient(create_app(corpus, financial_provider=LocalToolDouble())) as api:
        result = ask(api, "¿En cuánto cambió la utilidad neta de Grupo Faro de 3T24 a 3T25?")
    assert result["status"] == "answered" and "12.29" in result["answer"]


@pytest.mark.parametrize("different_definition", [False, True])
def test_numbered_rate_footnote_controls_cross_document_comparison(corpus, different_definition):
    definition = "Utilidad neta / promedio del capital mayoritario"
    report(corpus.data / "A-base.pdf", ("3T24", "9M24"), ("111.11", "280.05"),
           roe_definition=definition, roe_values=("22.9%", "18.0%"))
    report(corpus.data / "B-consultado.pdf", ("3T25", "9M25"), ("123.40", "310.10"),
           roe_definition=definition if not different_definition else "Utilidad neta / capital de cierre",
           roe_values=("23.6%", "18.1%"))
    corpus.index()
    with TestClient(create_app(corpus, financial_provider=LocalToolDouble())) as api:
        answer = ask(api, DIFF.replace("la utilidad neta", "ROE"))
    if different_definition:
        assert answer["status"] == "abstained" and "definición" in answer["answer"]
    else:
        assert answer["status"] == "answered"
        assert "0.7 puntos porcentuales" in answer["answer"] and "% %" not in answer["answer"]
        assert {item["filename"] for item in answer["citations"]} == {"A-base.pdf", "B-consultado.pdf"}
        assert all(item["pdf_page"] == 2 and "ROE (2)" in item["snippet"] for item in answer["citations"])


def test_abstention_cites_reexpression_without_using_flagged_operand(corpus):
    report(corpus.data / "B-consultado.pdf", ("3T25", "9M25"), ("123.40", "310.10"),
           note="La desconsolidación de Bineo cambia la base de las cifras.")
    corpus.index()
    with TestClient(create_app(corpus, financial_provider=LocalToolDouble())) as api:
        result = ask(api)
    assert result["status"] == "abstained" and "cambio de perímetro" in result["answer"]
    assert "123.40" not in result["answer"] and "desconsolidación de Bineo" in result["answer"]
    notes = [c for c in result["citations"] if c["evidence_id"].endswith(":nota")]
    assert [(c["filename"], c["pdf_page"], c["snippet"]) for c in notes] == [
        ("B-consultado.pdf", 2, "La desconsolidación de Bineo cambia la base de las cifras."),
    ]


def market_report(path, layout, *, duplicate_period=False, reverse_rows=False):
    """Tabla sin divisiones internas, con dos monedas y una comparación porcentual."""
    import pymupdf

    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((40, 55), "Grupo Faro consolidado")
        page = pdf.new_page()
        page.draw_rect((25, 65, 555, 190))
        page.insert_text((38, 94), "Información de la Acción del Grupo", fontsize=10)
        page.insert_text((480, 83), "Var. Vs.", fontsize=9)
        page.insert_text((480, 106), "1T24", fontsize=9)

        def insert_column(x, y, text, size):
            width = pymupdf.get_text_length(text, fontsize=size)
            page.insert_text((x - width / 2, y), text, fontsize=size)

        dollar_y, peso_y = (157, 136) if reverse_rows else (136, 157)
        for index, (x, period, dollars, pesos) in enumerate(layout):
            insert_column(x, 94, "1T24" if duplicate_period and index == 0 else period, 10)
            insert_column(x, dollar_y, dollars, 10)
            insert_column(x, peso_y, pesos, 10)
        page.insert_text((38, dollar_y), "Capitalización de mercado (Millones de dólares)", fontsize=9)
        page.insert_text((38, peso_y), "Capitalización de mercado (Millones de pesos)", fontsize=9)
        page.insert_text((480, dollar_y), "(28%)", fontsize=9)
        page.insert_text((480, peso_y), "(20%)", fontsize=9)
        page.insert_text((38, 180), "Precio de referencia 1,234.50", fontsize=9)
        pdf.save(path)


@pytest.mark.parametrize("currency,expected,operands,layout", [
    ("dólares", "-8461 millones de dólares", ("30,761", "22,300"),
     [(264, "2T24", "22,300", "406,931"), (340, "1T24", "30,761", "508,555"),
      (419, "3T23", "23,762", "407,173")]),
    ("pesos", "-101624 millones de pesos", ("508,555", "406,931"),
     [(280, "3T23", "23,762", "407,173"), (358, "2T24", "22,300", "406,931"),
      (437, "1T24", "30,761", "508,555")]),
])
def test_market_capitalization_matches_period_and_currency(tmp_path, currency, expected, operands, layout):
    sources = tmp_path / "sources"
    sources.mkdir()
    market_report(sources / "tabla-variable.pdf", layout, reverse_rows=currency == "pesos")
    corpus = Corpus(sources, tmp_path / "db")
    corpus.index()
    with TestClient(create_app(corpus, financial_provider=LocalToolDouble())) as api:
        result = ask(api, f"Compara capitalización de mercado (millones de {currency}) "
                          "de Grupo Faro entre 1T24 y 2T24")
        assert result["status"] == "answered" and expected in result["answer"]
        assert len(result["citations"]) == 2
        for cite, operand in zip(result["citations"], operands):
            assert cite["snippet"].endswith(operand) and currency in cite["snippet"]
            assert cite["filename"] == "tabla-variable.pdf" and cite["pdf_page"] == 2
            url = f'/api/documents/{cite["doc_id"]}/pages/2/image'
            assert api.get(url).content.startswith(b"\x89PNG")


def test_market_unit_before_periods_and_conflicting_suffix(tmp_path):
    data = tmp_path / "inputs"
    data.mkdir()
    market_report(data / "tabla.pdf", [
        (275, "1T24", "30,761", "508,555"),
        (365, "2T24", "22,300", "406,931"),
        (441, "3T23", "23,762", "407,173"),
    ])
    corpus = Corpus(data, tmp_path / "state")
    corpus.index()
    with TestClient(create_app(corpus, financial_provider=LocalToolDouble())) as api:
        question = "Compara la capitalización de mercado en millones de dólares entre 1T24 y 2T24"
        answer = ask(api, question + ". Indica ambos valores, la diferencia y las fuentes.")
        conflict = ask(api, question + " en millones de pesos")
    assert answer["status"] == "answered" and len(answer["citations"]) == 2
    assert all("dólares" in item["snippet"] for item in answer["citations"])
    assert conflict["status"] == "abstained" and "incompatibles" in conflict["answer"]
    assert not conflict["tools_used"] and not conflict["citations"]


@pytest.mark.parametrize("ambiguous", ["moneda", "periodo"])
def test_market_capitalization_abstains_on_ambiguous_row_or_header(tmp_path, ambiguous):
    data = tmp_path / "input"
    data.mkdir()
    layout = [(268, "3T23", "23,762", "407,173"), (348, "1T24", "30,761", "508,555"),
              (428, "2T24", "22,300", "406,931")]
    market_report(data / "tabla.pdf", layout, duplicate_period=ambiguous == "periodo")
    corpus = Corpus(data, tmp_path / "state")
    corpus.index()
    qualifier = " (millones de dólares)" if ambiguous == "periodo" else ""
    with TestClient(create_app(corpus, financial_provider=LocalToolDouble())) as api:
        result = ask(api, f"Compara capitalización de mercado{qualifier} entre 1T24 y 2T24")
    assert result["status"] == "abstained" and not result["citations"]


def test_stock_sum_is_rejected_without_reading_sources(corpus, monkeypatch):
    def unavailable():
        pytest.fail("La decisión de aditividad no debe depender del catálogo o la extracción.")

    monkeypatch.setattr(corpus, "catalog", unavailable)
    with TestClient(create_app(corpus, financial_provider=LocalToolDouble())) as api:
        result = ask(api, "Calcula la suma de activo total de Grupo Faro entre 3T24 y 3T25")
    assert result["status"] == "abstained"
    assert "saldo a una fecha de corte" in result["answer"] and "no es aditiva" in result["answer"]
    assert result["tools_used"] == [] and result["citations"] == []



def test_financial_prose_normalizes_periods_order_operations_and_units():
    from apps.api.financial_agent import parse_intent

    relative = parse_intent("Con base en el segundo trimestre de 2024, determina cuánto creció porcentualmente "
                            "la utilidad neta trimestral de Grupo Faro al tercer trimestre de ese año.")
    assert (relative.base.label, relative.current.label, relative.operation, relative.additional_difference) == (
        "2T24", "3T24", "percent_change", True,
    )
    share = parse_intent("¿Qué proporción representa la utilidad neta de 2T24 frente a la de los primeros seis meses de 2024?")
    assert (share.base.label, share.current.label, share.operation) == ("6M24", "2T24", "participation")
    market = parse_intent("En la tabla bursátil del cuarto trimestre de 2024, ¿cuánto cayó la capitalización de "
                          "mercado de Grupo Faro respecto al tercer trimestre, tanto en pesos como en dólares?")
    assert (market.base.label, market.current.label, market.currencies) == ("3T24", "4T24", ("pesos", "dólares"))
    with pytest.raises(Abstain, match="misma escala"):
        parse_intent("Compara capitalización de mercado de Grupo Faro entre 1T24 y 2T24 "
                     "tanto en miles de pesos como en millones de dólares")


def test_participation_needs_containment_same_table_and_same_basis():
    from dataclasses import replace
    from apps.api.finance import PERIOD, local_period

    def operand(period, number, column):
        return Operand(
            metric="utilidad neta", entity="Grupo Faro", period=local_period(PERIOD.fullmatch(period)),
            value=Decimal(number), original=number, unit=Unit("moneda", "MXN", Decimal(1), "MXN"),
            basis="consolidada", citation=Citation(doc_id="f" * 64, filename="tabla.pdf", pdf_page=1,
                                                   evidence_id=f"f:1:0:4:{column}", snippet=number),
        )

    whole, part = operand("9M24", "600", 2), operand("2T24", "150", 1)
    assert calculate("participation", whole, part)[:2] == (Decimal(25), "% de participación")
    with pytest.raises(Abstain, match="distinto tipo"):
        calculate("percent_change", whole, part)
    with pytest.raises(Abstain, match="no está incluido"):
        calculate("participation", whole, operand("4T24", "150", 1))
    with pytest.raises(Abstain, match="misma tabla"):
        calculate("participation", whole, replace(part, citation=part.citation.model_copy(update={"pdf_page": 2})))
    with pytest.raises(Abstain, match="bases contables"):
        calculate("participation", whole, replace(part, basis="individual"))


def test_indicator_stops_before_article_of_a_written_period():
    from apps.api.financial_agent import parse_intent

    intent = parse_intent("¿Cuánto bajó la capitalización de mercado en pesos entre el primer trimestre de 2024 y el segundo trimestre de ese año?")
    assert intent.metric == "capitalización de mercado"
    assert intent.output_currency == "pesos"
    assert (intent.base.label, intent.current.label) == ("1T24", "2T24")


def test_indicator_label_distinguishes_a_section_heading_from_a_second_row():
    from apps.api.financial_evidence import metric_label, row_label

    assert row_label("ROA (3)\nOperación:") == "ROA (3)"
    assert metric_label("ROA (3)\nOperación:") == "roa"
    assert metric_label("ROA (3)\nROE (2)") != "roa"
