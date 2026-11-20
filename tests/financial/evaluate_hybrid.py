"""Evalúa el híbrido sin red, o una instancia separada con alcance autorizado."""
import argparse
import json
import os
import re
import sys
from collections import Counter
from contextlib import ExitStack, redirect_stdout
from hashlib import file_digest
from pathlib import Path
from time import perf_counter
from urllib.request import urlopen

import pymupdf
from fastapi.testclient import TestClient

from apps.api.deepseek_fixture import HYBRID_QUESTIONS
from apps.api.hybrid_agent import MODE
from apps.api.hybrid_planner import DeterministicPlanner
from apps.api.main import create_app
from evaluate_acceptance import OPERATIONS, PARAPHRASES, QUESTIONS, assess as acceptance, contains, live, table_cell
from evaluate_adversarial import B_ORACLES, B_QUESTIONS, NEW, assess, inspect, original
from hybrid_holdout import K, K_OPERANDS
from visual_regression import DOCUMENTARY_EVIDENCE, OBSERVED, VISUAL, VISUAL_OPERANDS


LIQUIDITY = "EEFF 2025 Grupo_.pdf"
ANNUAL = "IA Banorte ESP_16.pdf"
QUARTER = "3T24.pdf"
PERIMETER = ("3T25_vc.pdf", 5, "no son comparables con aquellas presentadas en los periodos respectivos")
DEFINITION = (LIQUIDITY, 153, "relación entre Activos Líquidos y Salidas Netas de Efectivo")
MEASURES = (LIQUIDITY, 153, "plan de financiamiento de contingencia")
OBJECTIVES = (LIQUIDITY, 152, "Medir la vulnerabilidad de la Institución a condiciones extremas de mercado")

# Se fija la nueva muestra con fuentes antes del primer POST. La opción
# check-oracles coteja la frase fuente. Para montos se requiere geometría de
# fila y columna además de las unidades y las operaciones esperadas.
INDEPENDENT = {
    "J01": ("¿Cómo está segmentado el portafolio de GFNorte para fines de gestión del riesgo de crédito?",
            "answered", ("minorista", "mayorista"), ((ANNUAL, 29, "segmentamos nuestro portafolio"),)),
    "J02": ("¿Qué controles menciona el informe anual de Banorte durante la originación de crédito?",
            "answered", ("identificación exhaustiva", "validación robusta"), ((ANNUAL, 30, "Identificación exhaustiva del cliente"),)),
    "J03": ("¿Qué objetivo contempla la exposición a condiciones extremas y cómo se mide por separado la cobertura de liquidez?",
            "answered", ("vulnerabilidad", "activos líquidos", "salidas netas de efectivo"), (OBJECTIVES, DEFINITION)),
    "J04": ("¿Con qué frecuencia se informa al CPR y al Consejo sobre el cumplimiento de los límites de liquidez?",
            "answered", ("mensuales al CPR", "trimestral al Consejo"), (MEASURES,)),
    "J05": ("¿Qué herramientas de gestión se complementan con planes de contingencia en materia de liquidez de la Tenedora?",
            "answered", ("brechas de re-precio", "pruebas de estrés", "plan de financiamiento de contingencia"), (MEASURES,)),
    "J06": ("En el indicador que compara activos líquidos con egresos netos, ¿cuál es el horizonte del escenario regulatorio?",
            "answered", ("30 días", "estrés regulatorio"), (DEFINITION,)),
    "J07": ("¿Qué finalidad tiene el nivel de activos líquidos elegibles en el marco de riesgo de balance?",
            "answered", ("garantizar la liquidez", "condiciones de estrés"), ((LIQUIDITY, 152, "garantizar la liquidez de la Institución"),)),
    "J08": ("¿Se pueden atribuir a todas las filiales las políticas de la Tenedora que aparecen en el capítulo de liquidez de los estados financieros de 2025?",
            "answered", ("no acredita",), ((LIQUIDITY, 152, "Las políticas de Riesgo de Liquidez en la Tenedora contemplan"),)),
    "J09": ("Al comparar el ROE de GFNorte en 3T23 y 3T24, ¿qué brecha queda expresada en puntos porcentuales?",
            "answered", ("21.5%", "22.9%", "1.4 puntos porcentuales"), ((QUARTER, 6, "ROE (2)"),)),
    "J10": ("¿En cuánto cambió el activo total de GFNorte de 2T24 a 3T24? Expresa la diferencia en millones de pesos.",
            "answered", ("2,435,012", "2,420,031", "-14981 millones de pesos"), ((QUARTER, 6, "Activo Total"),)),
    "J11": ("¿Qué porcentaje representa la utilidad neta de 4T25 respecto de 9M25 en una participación del acumulado?",
            "abstained", ("no está incluido",), ()),
    "J12": ("¿En qué porcentaje mejoró la utilidad neta de GFNorte entre 3T23 y 3T24?",
            "answered", ("13,268", "14,238", "7.31 %"), ((QUARTER, 5, "Utilidad Neta"),)),
    "J13": ("En dólares, ¿de qué magnitud fue el retroceso porcentual de la capitalización de mercado entre 1T24 y 2T24?",
            "answered", ("30,761", "22,300", "-27.51 %"), (("2T24.pdf", 7, "Capitalización de Mercado"),)),
    "J14": ("¿En cuánto cambió el ROA de GFNorte entre 3T23 y 3T24? Indica también el cambio del ROE en esos trimestres.",
            "answered", ("0.1 puntos porcentuales", "1.4 puntos porcentuales"), ((QUARTER, 6, "ROA (3)"), (QUARTER, 6, "ROE (2)"))),
    "J15": ("¿Cuánto cayó la capitalización de mercado de GFNorte en 2T24 respecto al primero de ese mismo año? Usa las dos monedas publicadas.",
            "answered", ("-101624 millones de pesos", "-8461 millones de dólares"), (("2T24.pdf", 7, "Capitalización de Mercado"),)),
    "J16": ("Compara la utilidad neta de GFNorte de 3T23 a 3T24, expresada exclusivamente en francos suizos.",
            "abstained", ("moneda",), ()),
    "J17": ("¿Qué exigencia de liquidez aprobó la Tenedora para el ejercicio 2043?",
            "abstained", ("evidencia suficiente",), ()),
    "J18": ("Compara el ROA de Banco Nébula entre 3T23 y 3T24.",
            "abstained", ("entidad",), ()),
    "J19": ("Suma el pasivo total de GFNorte entre 2T24 y 3T24 para obtener un saldo combinado.",
            "abstained", ("no es aditiva",), ()),
    "J20": ("Compara la utilidad neta de GFNorte de 2T24 a 3T25. ¿Es válida la comparación según el perímetro de consolidación?",
            "abstained", ("Bineo", "sin base común verificada"), (PERIMETER,)),
}

REQUIRED_OPERANDS = {
    "J09": {("ROE (2)", "3T23", "21.5%"), ("ROE (2)", "3T24", "22.9%")},
    "J10": {("Activo Total", "2T24", "2,435,012"), ("Activo Total", "3T24", "2,420,031")},
    "J12": {("Utilidad Neta", "3T23", "13,268"), ("Utilidad Neta", "3T24", "14,238")},
    "J13": {("Capitalización de Mercado (Millones de dólares)", "1T24", "30,761"),
            ("Capitalización de Mercado (Millones de dólares)", "2T24", "22,300")},
    "J14": {("ROA (3)", "3T23", "2.3%"), ("ROA (3)", "3T24", "2.4%"),
            ("ROE (2)", "3T23", "21.5%"), ("ROE (2)", "3T24", "22.9%")},
    "J15": {("Capitalización de Mercado (Millones de dólares)", "1T24", "30,761"),
            ("Capitalización de Mercado (Millones de dólares)", "2T24", "22,300"),
            ("Capitalización de Mercado (Millones de pesos)", "1T24", "508,555"),
            ("Capitalización de Mercado (Millones de pesos)", "2T24", "406,931")},
}


SYNTHETIC_EXPECTED = {
    "indirect": ("answered", ("proporción de los ingresos",), {1}, 1),
    "definition": ("answered", ("proporción de los ingresos",), {1}, 1),
    "sections": ("answered", ("proporción de los ingresos", "reserva de efectivo"), {1, 2}, 1),
    "metrics": ("answered", ("12.29 millones de mxn", "1.5 puntos porcentuales"), {3}, 1),
    "entity_metric": ("abstained", ("distinto tipo o duración",), set(), 0),
    "complete": ("answered", ("12.29 millones de mxn",), {3}, 0),
    "invalid": ("abstained", ("no es aditiva",), set(), 0),
    "partial": ("answered", ("proporción de los ingresos", "respuesta parcial", "prometida"), {1}, 1),
    "absent": ("abstained", ("evidencia suficiente",), set(), 1),
    "restrictions": ("abstained", ("evidencia suficiente",), set(), 0),
}


def synthetic_score(case, row):
    status, phrases, pages, calls = SYNTHETIC_EXPECTED[case]
    valid = (row["http"] == 200 and row["provider_mode"] == MODE and row["status"] == status
             and row["consumo_deepseek"]["calls"] == str(calls)
             and all(cite["accessible"] for cite in row["citations"])
             and pages == {cite["pdf_page"] for cite in row["citations"]}
             and all(contains(row["answer"], phrase) for phrase in phrases)
             and not contains(row["answer"], "revelar_secretos"))
    return {**row, "veredicto": "PASS" if valid else "FAIL"}


def aligned(page, label, period, value):
    spaced = re.sub(r"([TM])(\d{2})$", r"\1 \2", period)
    return any(table_cell(page, label, header, value) for header in {period, spaced})


def inspect_independent(root, cite):
    checked = inspect(root, cite)
    fields = [field.strip() for field in cite["snippet"].split("|")]
    if checked["semantic"] or len(fields) != 3:
        return checked
    path = (root / cite["filename"]).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        return checked
    with path.open("rb") as stream:
        if file_digest(stream, "sha256").hexdigest() != cite["doc_id"]:
            return checked
    with pymupdf.open(path) as pdf:
        if 1 <= cite["pdf_page"] <= len(pdf) and aligned(pdf[cite["pdf_page"] - 1], *fields):
            checked.update(text=True, semantic=True)
    return checked


class SimulatedPlanner(DeterministicPlanner):
    def __init__(self):
        self.requests = Counter()

    async def plan(self, question, slots, totals):
        self.requests[question] += 1
        return await super().plan(question, slots, totals)


def test_row(client, case, question):
    start = perf_counter()
    with redirect_stdout(sys.stderr):
        response = client.post("/api/chat", json={"message": question})
    seconds = round(perf_counter() - start, 3)
    row = {
        "id": case, "question": question, "http": response.status_code, "segundos_post": seconds,
        **response.json(),
        "hibrido": {key.removeprefix("x-hybrid-"): value for key, value in response.headers.items()
                    if key.startswith("x-hybrid-")},
        "consumo_deepseek": {key.removeprefix("x-p2-deepseek-"): value for key, value in response.headers.items()
                             if key.startswith("x-p2-deepseek-")},
    }
    row.setdefault("answer", row.get("detail"))
    row.setdefault("status", None)
    row.setdefault("provider_mode", None)
    row.setdefault("tools_used", [])
    row.setdefault("citations", [])
    for cite in row["citations"]:
        image = client.get(f"/api/documents/{cite['doc_id']}/pages/{cite['pdf_page']}/image")
        cite["accessible"] = image.status_code == 200 and image.content.startswith(b"\x89PNG\r\n\x1a\n")
    return row


def score(root, row, oracle, label):
    mode = MODE if label.startswith("hybrid") else None
    if label == "financial-local" and row["id"].startswith(("J", "K")):
        documents = {*(f"J{i:02}" for i in range(1, 9)), "J17", "K01", "K02", "K03", "K04"}
        mode = "extractivo local" if row["id"] in documents else "financiero local (doble)"
    result = assess(root, row, oracle, expected_mode=mode,
                    citation_check=inspect_independent if row["id"].startswith(("J", "K")) else inspect)
    have = {tuple(part.strip() for part in cite["snippet"].split("|"))
            for cite, check in zip(row["citations"], result["cotejo"], strict=True) if check["semantic"]}
    required = (REQUIRED_OPERANDS | K_OPERANDS).get(row["id"], set())
    if result["veredicto"] == "PASS" and not required <= have:
        result["veredicto"] = "PARTIAL"
        result["missing_operands"] = sorted(required - have)
    return result


def score_visual(root, row, oracle, label):
    case = row["id"]
    mode = MODE if label == "hybrid-local" else (
        "extractivo local" if case.startswith("D") or case == "S04" else "financiero local (doble)"
    )
    result = assess(root, row, oracle, expected_mode=mode, citation_check=inspect_independent)
    pages = {(filename, page) for filename, page, _ in oracle[2]}
    matched = [(cite, check) for cite, check in zip(row["citations"], result["cotejo"], strict=True)
               if all(check.values())]
    operands = VISUAL_OPERANDS.get(case, set())
    have = {tuple(item.strip() for item in cite["snippet"].split("|")) for cite, _ in matched
            if (cite["filename"], cite["pdf_page"]) in pages}
    documentary = DOCUMENTARY_EVIDENCE.get(case, [])
    for cite, check in zip(row["citations"], result["cotejo"], strict=True):
        source = cite["filename"], cite["pdf_page"]
        check["pertinente"] = check["semantic"] and (
            (source in pages and tuple(item.strip() for item in cite["snippet"].split("|")) in operands)
            or any(source == (name, page) and any(contains(cite["snippet"], fact) for fact in facts)
                   for name, page, facts in documentary)
            # Una cifra observada con su celda también sirve como contexto de la abstención de perímetro.
            or (case == "S05" and cite["snippet"].count("|") == 2
                and " | 3T24 | " in cite["snippet"])
        )
    complete_documents = all(
        any((cite["filename"], cite["pdf_page"]) == (name, page)
            and all(contains(cite["snippet"], fact) for fact in facts) for cite, _ in matched)
        for name, page, facts in documentary
    )
    if result["veredicto"] == "PASS" and (not operands <= have or not complete_documents):
        result["veredicto"] = "PARTIAL"
    if case.startswith("F") and result["veredicto"] == "PARTIAL" and "financial_calculator" not in row["tools_used"]:
        result["veredicto"] = "FAIL"
    if (case == "S06" and row["http"] == 200 and row["status"] == "abstained"
            and "financial_calculator" not in row["tools_used"] and result["veredicto"] == "FAIL"):
        result["veredicto"] = "PARTIAL"
    result.update(execution=label, observado_visual=OBSERVED[case], comprobaciones=len(oracle[1]),
                  celdas_acreditadas=len(operands & have), celdas_esperadas=len(operands))
    return result


def emit(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)


def port(value):
    value = int(value)
    if not 1 <= value <= 65535:
        raise argparse.ArgumentTypeError("Puerto inválido.")
    return value


def verify_health(base, mode, size, scope=None):
    with urlopen(base + "/api/health", timeout=4) as response:
        state = json.load(response)
    if (state["provider_mode"] != mode or state["documents"] != size
            or (scope and (state.get("external_data_scope") != scope or not state.get("external_provider_ready")))):
        raise SystemExit("Modo o alcance inesperado en /api/health.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=("regression", "known-mock", "independent-local", "j-mock", "k-mock",
                                               "check-oracles", "synthetic", "known-live", "k-live", "visual-live",
                                               "known-local", "j-local", "k-local"))
    parser.add_argument("--data", type=Path)
    parser.add_argument("--port", type=port, default=8196)
    parser.add_argument("--local-port", type=port, default=8197)
    parser.add_argument("--authorized-real-data", action="store_true")
    parser.add_argument("--variant", choices=("both", "local", "mock"), default="both")
    args = parser.parse_args()
    if args.suite == "synthetic":
        base = f"http://127.0.0.1:{args.port}"
        verify_health(base, MODE, 1, "synthetic")
        for case, question in HYBRID_QUESTIONS.items():
            emit(synthetic_score(case, live(base, case, question)))
        return
    if not args.data:
        parser.error("Se requiere el directorio de datos.")
    root = args.data.resolve(strict=True)
    if args.suite == "check-oracles":
        cases = INDEPENDENT | K | VISUAL
        for source in sorted({ref for _, _, _, refs in cases.values() for ref in refs}):
            filename, page, snippet = source
            if not original(root / filename, page, snippet):
                raise SystemExit(f"Oráculo sin respaldo: {filename}, p. {page}.")
        for case, expected in (REQUIRED_OPERANDS | K_OPERANDS | VISUAL_OPERANDS).items():
            found = set()
            for filename, page, _ in cases[case][3]:
                with pymupdf.open(root / filename) as pdf:
                    found |= {operand for operand in expected if aligned(pdf[page - 1], *operand)}
            if found != expected:
                raise SystemExit(f"Operandos fuera de contexto en {case}.")
        emit({"oracle_count": len(cases), "verified_sources": True, "verified_operands": True})
        return
    if args.suite == "visual-live":
        local = f"http://127.0.0.1:{args.local_port}"
        hybrid = f"http://127.0.0.1:{args.port}"
        verify_health(local, "financiero local (doble)", 24)
        with urlopen(hybrid + "/api/health", timeout=4) as response:
            state = json.load(response)
        if (state.get("provider_mode") != MODE or state.get("documents") != 24
                or state.get("external_data_scope") != "blocked"
                or state.get("planner") != "deterministic" or state.get("external_provider_ready") is not False):
            parser.error("Se requiere un backend híbrido determinista con salida bloqueada.")
        for case, (question, *oracle) in VISUAL.items():
            for label, base in (("financial-local", local), ("hybrid-local", hybrid)):
                row = live(base, case, question)
                if label == "hybrid-local":
                    usage = row.get("consumo_deepseek", {})
                    if any(float(usage.get(key, -1)) != 0 for key in ("calls", "input", "output", "usd-upper")):
                        raise SystemExit("Faltan métricas o se detectó consumo externo.")
                emit(score_visual(root, row, oracle, label))
        return
    if args.suite in {"known-live", "k-live"}:
        if not args.authorized_real_data:
            parser.error("La comparación real requiere autorización independiente.")
        local = f"http://127.0.0.1:{args.local_port}"
        hybrid = f"http://127.0.0.1:{args.port}"
        verify_health(hybrid, MODE, 24, "authorized")
        variants = (("hybrid-real", hybrid),)
        if args.suite == "known-live":
            verify_health(local, "financiero local (doble)", 24)
            variants = (("financial-local", local), *variants)
        cases = K if args.suite == "k-live" else NEW
        for case, (question, *oracle) in cases.items():
            for label, base in variants:
                emit({**score(root, live(base, case, question), oracle, label), "execution": label})
        return
    # Local con un planificador en proceso para medir el techo del mecanismo.
    # Las otras pasadas de esta rama conservan el bloqueo de egress.
    os.environ["HYBRID_DEEPSEEK_SCOPE"] = "blocked"
    simulated = SimulatedPlanner() if args.suite in {"known-mock", "j-mock", "k-mock"} else None
    with ExitStack() as stack:
        os.environ["LLM_PROVIDER"] = "financial-local"
        local = stack.enter_context(TestClient(create_app())) if args.variant != "mock" else None
        if args.suite == "regression":
            for case, question in {**QUESTIONS, **PARAPHRASES, **OPERATIONS}.items():
                emit(acceptance(root, test_row(local, case, question)))
            for case, question in B_QUESTIONS.items():
                emit({**assess(root, test_row(local, case, question), B_ORACLES[case]), "execution": "financial-local"})
            return
        os.environ["LLM_PROVIDER"] = "hybrid-experimental"
        hybrid = stack.enter_context(TestClient(create_app(hybrid_planner=simulated))) if args.variant != "local" else None
        cases = {"known-mock": NEW, "known-local": NEW, "k-mock": K, "k-local": K}.get(args.suite, INDEPENDENT)
        for case, (question, *oracle) in cases.items():
            for label, client in (("financial-local", local), ("hybrid-mock" if simulated else "hybrid-local", hybrid)):
                if client is None:
                    continue
                row = score(root, test_row(client, case, question), oracle, label)
                row["execution"] = label
                row["simulated_plans"] = simulated.requests[question] if simulated and label == "hybrid-mock" else 0
                emit(row)


if __name__ == "__main__":
    main()
