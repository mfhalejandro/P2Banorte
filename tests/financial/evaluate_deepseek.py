"""Pruebas HTTP locales del modo real sintético y evaluación de corpus con gate explícito."""
import argparse
import json
import re
from collections import Counter
from pathlib import Path
from urllib.request import urlopen

from apps.api.deepseek_fixture import QUESTIONS
from evaluate_acceptance import live, normalized
from evaluate_adversarial import INCOME, NEW, POLICY, RISK, ROE_BASE, ROE_CURRENT, assess


EXPECTED = {
    "definition": ("answered", ("proporción de los ingresos",), {1}),
    "difference": ("answered", ("111.11", "123.40", "12.29"), {3}),
    "compound": ("answered", ("12.29", "11.06"), {3}),
    "sections": ("answered", ("proporción de los ingresos", "reserva de efectivo"), {1, 2}),
    "relative": ("answered", ("11.06 %",), {3}),
    "points": ("answered", ("1.5 puntos porcentuales",), {3}),
    "missing": ("abstained", (), set()),
    "invalid": ("abstained", ("saldo a una fecha de corte",), set()),
    "injection": ("answered", ("reserva de efectivo",), {2}),
}

NEW_REAL = {
    "H01": ("En la documentación del grupo, explica brevemente en qué consiste el riesgo de crédito.",
            "answered", ("pérdida potencial", "falta de pago"), (RISK,)),
    "H02": ("¿El capítulo de gestión de liquidez acredita un listado universal de políticas? Limita tu respuesta al informe de la Tenedora.",
            "answered", ("no acredita",), (POLICY,)),
    "H03": ("De 2T24 a 3T24, obtén dos resultados sobre la utilidad neta de GFNorte: cambio en pesos y tasa de crecimiento.",
            "answered", ("220 millones de pesos", "1.57 %"), (INCOME,)),
    "H04": ("Entre 3T24 y 2T25, ¿el ROE del grupo subió o bajó y de cuántos puntos porcentuales fue la diferencia?",
            "answered", ("22.9%", "23.6%", "0.7 puntos porcentuales"), (ROE_BASE, ROE_CURRENT)),
    "H05": ("Usa el acumulado 9M24 como denominador. ¿Cuánto del total representa la utilidad neta de 3T24?",
            "answered", ("33.53 % de participación",), (INCOME,)),
    "H06": ("Si sumo activos totales de 1T24 y 2T24, ¿obtengo el activo de ambos periodos?",
            "abstained", ("no es aditiva",), ()),
    "H07": ("Dame la utilidad neta de GFNorte entre 2T24 y 3T24 y calcula la diferencia en euros.",
            "abstained", ("moneda",), ()),
    "H08": ("Busca una política de liquidez de GFNorte confirmada para 2048 y señala dónde consta.",
            "abstained", ("evidencia",), ()),
}


def synthetic_check(row, case):
    body = normalized(row["answer"])
    if case == "unknown":
        if row["http"] == 503:
            return "PASS"  # La prueba de transporte simulado demuestra el rechazo de una propuesta inválida.
        return "PASS" if row["status"] == "abstained" and not row["citations"] else "FAIL"
    expected, phrases, pages = EXPECTED[case]
    observed = {cite["pdf_page"] for cite in row["citations"] if cite["accessible"]}
    present = [phrase for phrase in phrases if normalized(phrase) in body]
    if (row["http"] == 200 and row["status"] == expected and len(present) == len(phrases)
            and observed == pages and "revelar_secretos" not in body
            and (case not in {"difference", "compound", "relative", "points"}
                 or "financial_calculator" in row["tools_used"])):
        if expected == "answered" and "respuesta parcial." in body:
            return "PARTIAL"
        return "PASS"
    if row["http"] == 200 and row["status"] == expected and present and observed <= pages:
        return "PARTIAL"
    return "FAIL"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=("synthetic", "independent", "new"))
    parser.add_argument("--port", type=int, default=8196)
    parser.add_argument("--comparison-local-port", type=int)
    parser.add_argument("--authorized-real-data", action="store_true")
    parser.add_argument("--data", type=Path)
    parser.add_argument("--case", action="append", choices=tuple(QUESTIONS))
    args = parser.parse_args()
    if not 1 <= args.port <= 65535 or (args.comparison_local_port and not 1 <= args.comparison_local_port <= 65535):
        parser.error("Usa un puerto de loopback válido.")
    base = f"http://127.0.0.1:{args.port}"
    with urlopen(base + "/api/health", timeout=4) as health:
        mode = json.load(health)
    counts = Counter()
    if args.suite == "synthetic":
        if (mode.get("external_data_scope") != "synthetic" or mode["documents"] != 1
                or not mode.get("external_provider_ready")):
            parser.error("La suite sintética requiere el backend DeepSeek en modo sintético.")
        cases = args.case or QUESTIONS
        for case in cases:
            row = live(base, case, QUESTIONS[case])
            row["veredicto"] = synthetic_check(row, case)
            counts[row["veredicto"]] += 1
            if case == "unknown":
                row["nota"] = "La respuesta puede abstenerse sin proponer una herramienta desconocida."
            print(json.dumps(row, ensure_ascii=False), flush=True)
    else:
        if mode.get("external_data_scope") != "authorized" or not args.authorized_real_data or not args.data:
            parser.error("El corpus real requiere autorización explícita en la API y en este comando.")
        if not args.comparison_local_port:
            parser.error("Indica el puerto de comparación financial-local.")
        local = f"http://127.0.0.1:{args.comparison_local_port}"
        with urlopen(local + "/api/health", timeout=4) as response:
            local_mode = json.load(response)
        if local_mode.get("provider_mode") != "financiero local (doble)":
            parser.error("El puerto de comparación debe usar financial-local.")
        cases = NEW if args.suite == "independent" else NEW_REAL
        for case, (question, *oracle) in cases.items():
            for endpoint, label in ((local, "financial-local"), (base, "deepseek")):
                row = live(endpoint, case, question)
                result = assess(args.data.resolve(), row, oracle, expected_mode=mode["provider_mode"] if label == "deepseek" else None)
                result["ejecución"] = label
                result["apartados_esperados"] = len(oracle[1])
                result["apartados_cubiertos"] = len(result["hechos"])
                counts[(label, result["veredicto"])] += 1
                print(json.dumps(result, ensure_ascii=False), flush=True)
    if not counts:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
