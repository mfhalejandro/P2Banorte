"""Aceptación dirigida del corpus de ensayo. Lectura local, sin ingesta."""
import argparse
from decimal import Decimal
from hashlib import sha256
from ipaddress import ip_address
import json
from pathlib import Path
import re
from time import perf_counter
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import pymupdf

QUESTIONS = {
    "D01": "¿Qué es el riesgo de crédito?",
    "D02": "¿Qué políticas de liquidez se mencionan?",
    "D03": "¿Qué políticas de liquidez adoptará Banorte en el año 2035?",
    "F01": ("Compara la capitalización de mercado en millones de dólares entre 1T24 y 2T24. "
            "Indica ambos valores, la diferencia y las fuentes."),
    "F02": ("Compara la utilidad neta de GFNorte entre 3T24 y 3T25. "
            "¿Cuál fue la variación y existe alguna advertencia que afecte la comparabilidad?"),
    "F03": "Calcula la variación porcentual de la utilidad neta de GFNorte.",
}
PARAPHRASES = {
    "D02a": ("¿Cuáles son las políticas de riesgo de liquidez de la Tenedora? "
             "Enumera las políticas identificadas y señala en qué documento y página se encuentra cada una."),
    "D02b": ("Señala en qué documento y página se encuentra cada una. "
             "¿Cuáles son las políticas de riesgo de liquidez de la Tenedora?"),
    "D02c": ("Con documento y página para cada política, "
             "enumera las políticas de riesgo de liquidez de la Tenedora."),
    "D02d": ("Enumera las políticas de riesgo de liquidez de la Tenedora "
             "e indica el documento y la página de cada una."),
    "D03a": ("Cita la fuente y la página. "
             "¿Qué políticas de riesgo de liquidez de la Tenedora se mencionan en el año 2035?"),
}
OPERATIONS = {
    "P01": ("¿Cómo se define el riesgo de crédito en los informes de Banorte? "
             "Indica el documento y la página donde aparece la definición."),
    "P02": ("¿Cuáles son las principales políticas de riesgo de balance y liquidez de la Tenedora? "
             "Preséntalas en una lista e indica su fuente."),
    "P03": "¿Qué nuevas políticas de liquidez implementará GFNorte en 2035 según los informes disponibles?",
    "P04": ("¿En qué porcentaje aumentó la utilidad neta de GFNorte del 2T24 al 3T24? "
             "Muestra los valores utilizados y cita las fuentes."),
    "P05": ("¿Cómo cambió el ROE de GFNorte entre 3T24 y 2T25? "
             "Expresa la diferencia en puntos porcentuales e indica ambas fuentes."),
    "P06": ("Para la capitalización de mercado de GFNorte expresada en millones de pesos, "
             "¿cuál fue el cambio entre 1T24 y 2T24? Indica ambos valores."),
    "P07": "Calcula la variación de la utilidad neta de GFNorte entre 3T24 y 9M24. Explica si los periodos son comparables.",
    "P08": "Suma el activo total de GFNorte de 1T24 y 2T24 e indica el resultado en millones de pesos.",
    "P01a": "Cita la fuente y la página. ¿Qué significa el riesgo de crédito en los reportes de Banorte?",
    "P01b": "¿Cómo se define el riesgo de crédito en los documentos de Banorte?",
    "P02a": "Con la fuente y la página, enumera las políticas de riesgo de balance y liquidez de la Tenedora.",
    "P02b": "¿Qué políticas de riesgo de balance y liquidez de la Tenedora se mencionan? Preséntalas en viñetas.",
    "P04a": "Entre 2T24 y 3T24, ¿en qué porcentaje subió la utilidad neta de GFNorte? Cita ambas fuentes.",
    "P04b": "Cita las fuentes. ¿En qué porcentaje se incrementó la utilidad neta de GFNorte entre 2T24 y 3T24?",
    "P05a": "¿Cuánto varió el ROE de GFNorte de 3T24 a 2T25? Expresa el cambio en puntos porcentuales.",
    "P05b": "Para el ROE de GFNorte, ¿cuál fue la diferencia entre 3T24 y 2T25? En puntos porcentuales.",
    "P06a": ("Sobre la capitalización de mercado en millones de pesos de GFNorte, "
              "¿cuál fue la diferencia entre 1T24 y 2T24?"),
    "P06b": ("Cita ambas fuentes. ¿En cuánto cambió la capitalización de mercado de GFNorte "
              "entre 1T24 y 2T24 en millones de pesos?"),
    "N03": ("¿Cuáles son las políticas de riesgo de balance y liquidez de la Tenedora previstas para 2035? "
             "Indica la fuente."),
    "N07": "¿Cómo cambió la utilidad neta de GFNorte del 3T24 al 9M24? Indica ambas fuentes.",
    "N08": "En los estados publicados, ¿cómo cambió la utilidad neta de GFNorte entre 3T24 y 3T25?",
    "P03b": "Enumera las políticas de liquidez que GFNorte adoptará en 2035. Cita la fuente.",
    "P07b": "Entre 3T24 y 9M24, ¿en qué porcentaje cambió la utilidad neta de GFNorte?",
    "P08a": "Para el activo total de GFNorte, ¿cuál fue la suma entre 1T24 y 2T24?",
    "P08b": "Cita las fuentes. Calcula la suma del activo total de GFNorte entre 1T24 y 2T24.",
    "N09": ("Para la capitalización de mercado de GFNorte expresada en millones de pesos, "
             "¿cuál fue el cambio entre 1T24 y 2T24? Expresa el resultado en millones de dólares."),
    "N10": "¿Cómo cambió el ROE de Banco Inventado entre 3T24 y 2T25?",
    "N11": ("¿Cómo cambió la utilidad neta de GFNorte entre 2T24 y 3T24? "
             "Expresa la diferencia en puntos porcentuales."),
}
OPERATIONAL_ALIASES = {"P01": "D01", "P02": "D02", "P03": "D03", "P07": "N07", "N03": "D03", "N08": "F02"}
OPERAND_ORACLES = {
    "P04": ("Utilidad Neta", "millones de pesos", [
        ("3T24.pdf", 5, "2T24", "14,018"), ("3T24.pdf", 5, "3T24", "14,238"),
    ]),
    "P05": ("ROE", "%", [
        ("4T24_1.pdf", 6, "3T24", "22.9%"), ("2T25_vc_.pdf", 6, "2T25", "23.6%"),
    ]),
    "P06": ("Capitalización de Mercado (Millones de pesos)", "millones de pesos", [
        ("2T24.pdf", 7, "1T24", "508,555"), ("2T24.pdf", 7, "2T24", "406,931"),
    ]),
    "N07": ("Utilidad Neta", "millones de pesos", [
        ("3T24.pdf", 5, "3T24", "14,238"), ("3T24.pdf", 5, "9M24", "42,464"),
    ]),
    "N11": ("Utilidad Neta", "millones de pesos", [
        ("3T24.pdf", 5, "2T24", "14,018"), ("3T24.pdf", 5, "3T24", "14,238"),
    ]),
}
POLICY_HEADING = "Las políticas de Riesgo de Liquidez en la Tenedora contemplan:"
POLICIES = (
    "El establecimiento de Límites Globales y Específicos de Administración de Riesgo de Balance y Liquidez.",
    "La medición y monitoreo del Riesgo de Balance y Liquidez.",
    "La información y revelación del Riesgo de Liquidez a las áreas tomadoras de riesgos, al CPR, al Consejo de Administración, "
    "a las Autoridades Financieras y al Público Inversionista.",
)
RISK_TEXT = ("La pérdida potencial por la falta de pago de un acreditado o contraparte, incluyendo "
             "las garantías otorgadas, representa un riesgo para nuestro desempeño y plan estratégico en GFNorte.")
CAPITALIZATION = "Capitalización de Mercado (Millones de dólares)"


def normalized(text):
    return " ".join(text.casefold().split())


def contains(original, excerpt):
    return normalized(excerpt) in normalized(original)


def table_cell(page, caption, period, value):
    """Cotejo geométrico independiente del parser de la aplicación."""
    labels = page.search_for(caption)
    values = page.search_for(value)
    headers = page.search_for(period)
    return any(
        label.x1 < cell.x0
        and abs((label.y0 + label.y1) - (cell.y0 + cell.y1)) < 3
        and abs((head.x0 + head.x1) - (cell.x0 + cell.x1)) < 24
        and cell.y0 - 275 < head.y0 < cell.y0
        for label in labels for cell in values for head in headers
    )


def inspect_citation(root, case, citation):
    file = (root / citation["filename"]).resolve()
    original = file.is_relative_to(root) and file.is_file()
    result = {"documento": citation["filename"], "página_pdf": citation["pdf_page"],
              "accesible": citation["accessible"], "textual": False, "semántica": False}
    if not original:
        return result
    data = file.read_bytes()
    if sha256(data).hexdigest() != citation["doc_id"]:
        return result
    page_number = citation["pdf_page"]
    snippet = citation["snippet"]
    with pymupdf.open(stream=data, filetype="pdf") as pdf:
        if not 1 <= page_number <= len(pdf):
            return result
        page = pdf[page_number - 1]
        raw = page.get_text()
        layout = page.get_text(sort=True)
        if case == "D01":
            result["textual"] = contains(raw, RISK_TEXT) and contains(snippet, RISK_TEXT)
            contiguous = any(contains(raw, "Riesgo de crédito " + RISK_TEXT) for raw in (raw, layout))
            result["semántica"] = result["textual"] and contiguous and (file.name, page_number) == ("IA Banorte ESP_16.pdf", 29)
        elif case == "D02":
            item_coverage = [contains(layout, item) and contains(snippet, item) for item in POLICIES]
            result["textual"] = all(item_coverage) and contains(layout, POLICY_HEADING) and contains(snippet, POLICY_HEADING)
            title = page.search_for(POLICY_HEADING)
            rows = [page.search_for(item) for item in POLICIES]
            market = page.search_for("La pérdida potencial al cierre")
            footer = page.search_for("150")
            ordered = (title and market and footer and all(rows)
                       and market[0].y0 < title[0].y0 < rows[0][0].y0 < rows[1][0].y0 < rows[2][0].y0 < footer[0].y0)
            result["semántica"] = bool(result["textual"] and ordered and (file.name, page_number) == ("EEFF 2025 Grupo_.pdf", 152))
        elif case == "F01":
            fields = [part.strip() for part in snippet.split("|")]
            if len(fields) == 3:
                label, period, value = fields
                result["textual"] = all(contains(layout, item) for item in fields)
                expected = {"1T24": "30,761", "2T24": "22,300"}
                result["semántica"] = (result["textual"] and (file.name, page_number) == ("2T24.pdf", 7)
                                      and normalized(label) == normalized(CAPITALIZATION)
                                      and expected.get(period) == value and table_cell(page, label, period, value))
        elif case in OPERAND_ORACLES:
            fields = [part.strip() for part in snippet.split("|")]
            if len(fields) == 3:
                label, period, value = fields
                caption, unit, allowed = OPERAND_ORACLES[case]
                metric = label.removesuffix(" (2)")
                result["textual"] = all(contains(layout, item) for item in (metric, period, value))
                context = ("utilidad neta del periodo anualizada / promedio del capital contable mayoritario"
                           if unit == "%" else unit)
                result["semántica"] = (
                    result["textual"] and normalized(metric) == normalized(caption)
                    and (file.name, page_number, period, value) in allowed
                    and contains(layout, context) and table_cell(page, metric, period, value)
                )
        elif case == "F02":
            if file.name == "3T25_vc.pdf" and page_number in (3, 5):
                result["textual"] = contains(raw, snippet)
                result["semántica"] = (result["textual"] and "bineo" in normalized(snippet)
                                      and "desconsolid" in normalized(snippet) and "no son comparables" in normalized(snippet))
            elif file.name in ("4T24_1.pdf", "3T24.pdf") and page_number == 5:
                fields = [part.strip() for part in snippet.split("|")]
                result["textual"] = fields == ["Utilidad Neta", "3T24", "14,238"] and all(contains(layout, item) for item in fields)
                result["semántica"] = (result["textual"] and contains(layout, "millones de pesos")
                                      and table_cell(page, *fields))
    return result


def assess(root, row):
    family = row["id"][:3]
    case = OPERATIONAL_ALIASES.get(family, family)
    evidence = [inspect_citation(root, case, cite) for cite in row["citations"]]
    supported = all(all(item[key] for key in ("accesible", "textual", "semántica")) for item in evidence)
    status, answer, tools = (row[key] for key in ("status", "answer", "tools_used"))
    correct_mode = row["provider_mode"] == ("extractivo local" if case[0] == "D" else "financiero local (doble)")
    verdict, reason = "FAIL", "La respuesta no cumple el oráculo."
    if row["http"] != 200 or not correct_mode:
        reason = "HTTP o modo incorrecto."
    elif case == "D01" and status == "answered" and len(evidence) == 1 and supported and contains(answer, RISK_TEXT):
        verdict, reason = "PASS", "Define el concepto solicitado con su contexto."
    elif case == "D02" and status == "answered":
        bullets = [item.strip() for item in answer.split("•")[1:]]
        correct_content = len(evidence) == 1 and supported and len(bullets) == 3 and all(
            contains(actual, expected) for actual, expected in zip(bullets, POLICIES)
        )
        clean_and_scoped = bullets == list(POLICIES) and contains(answer, "La selección es parcial.")
        if correct_content:
            verdict = "PASS" if clean_and_scoped else "PARTIAL"
            reason = ("Las tres políticas están respaldadas y el alcance está acotado." if clean_and_scoped
                      else "Las políticas son pertinentes, pero se incluye el folio o falta acotar el alcance.")
    elif case == "D03" and status == "abstained" and not evidence and contains(answer, "evidencia suficiente"):
        verdict, reason = "PASS", "Se abstiene sobre el futuro sin inventar una política."
    elif case == "F01" and status == "answered":
        delta = re.search(r"A − B = ([-−]?\d[\d,]*) millones de dólares", answer)
        counts = {cite["snippet"].split("|")[1].strip() for cite in row["citations"] if "|" in cite["snippet"]}
        if (len(evidence) == 2 and supported and counts == {"1T24", "2T24"}
                and contains(answer, "(1T24): 30,761 millones de dólares")
                and contains(answer, "(2T24): 22,300 millones de dólares")
                and delta and Decimal(delta[1].replace("−", "-").replace(",", "")) == Decimal(22300) - Decimal(30761)
                and "financial_calculator" in tools):
            verdict, reason = "PASS", "Verifica ambos cruces fila/columna, moneda, escala y diferencia."
    elif case == "F02" and status == "abstained" and "financial_calculator" not in tools and contains(answer, "sin base común verificada"):
        if len(evidence) == 2 and supported and contains(answer, "desconsolidación de Bineo") and contains(answer, "14,238 millones de pesos"):
            verdict, reason = "PASS", "Cita la advertencia real y diferencia la cifra aislada de un cálculo comparable."
        else:
            verdict, reason = "PARTIAL", "Se abstiene, pero el texto de la advertencia o su procedencia son incompletos."
    elif case in {"P04", "P05", "P06"} and status == "answered":
        required = {
            "P04": ("(2T24): 14,018 millones de pesos", "(3T24): 14,238 millones de pesos", "= 1.57 %"),
            "P05": ("(3T24): 22.9%", "(2T25): 23.6%", "= 0.7 puntos porcentuales"),
            "P06": ("(1T24): 508,555 millones de pesos", "(2T24): 406,931 millones de pesos",
                    "= -101624 millones de pesos"),
        }
        operand_periods = {cite["snippet"].split("|")[1].strip() for cite in row["citations"] if "|" in cite["snippet"]}
        if (len(evidence) == 2 and supported and "financial_calculator" in tools
                and operand_periods == {operand[2] for operand in OPERAND_ORACLES[case][2]}
                and all(contains(answer, item) for item in required[case])):
            verdict, reason = "PASS", "Operación, resultado, unidad y dos operandos coinciden con los originales."
    elif case in {"N07", "N09", "N10", "N11"} and status == "abstained":
        cause = {"N07": "distinto tipo o duración", "N09": "incompatibles",
                 "N10": "entidad", "N11": "diferencia entre tasas"}[case]
        expected_citations = 2 if case in {"N07", "N11"} else 0
        if len(evidence) == expected_citations and supported and contains(answer, cause):
            verdict, reason = "PASS", "Abstención por la restricción solicitada, con las citas aplicables."
    elif case == "P08" and status == "abstained" and not tools and not evidence:
        if contains(answer, "saldo a una fecha de corte") and contains(answer, "no es aditiva"):
            verdict, reason = "PASS", "Rechazo de suma de saldos antes de buscar o calcular."
    elif case == "F03" and status == "abstained" and not evidence and not tools and contains(answer, "dos periodos distintos"):
        verdict, reason = "PASS", "Pide los periodos antes de consultar el corpus."
    return {**row, "veredicto": verdict, "justificación": reason, "validación_citas": evidence}


def live(base, case, question):
    request = Request(base + "/api/chat", data=json.dumps({"message": question}).encode(),
                      headers={"Content-Type": "application/json"})
    start = perf_counter()
    try:
        with urlopen(request, timeout=35) as resp:
            code, row = resp.status, json.load(resp)
            headers = resp.headers
    except HTTPError as exc:
        code = exc.code
        headers = exc.headers
        error = json.load(exc).get("detail") if exc.headers.get_content_type() == "application/json" else None
        row = {"answer": error or "HTTP " + str(code), "status": None, "provider_mode": None, "tools_used": [], "citations": []}
    elapsed = round(perf_counter() - start, 3)
    metrics = {key.lower().removeprefix("x-p2-deepseek-"): value for key, value in headers.items()
               if key.lower().startswith("x-p2-deepseek-")}
    if metrics:
        row["consumo_deepseek"] = metrics
    for cite in row["citations"]:
        url = f'{base}/api/documents/{cite["doc_id"]}/pages/{cite["pdf_page"]}/image'
        try:
            with urlopen(url, timeout=25) as image:
                cite["accessible"] = image.getheader("Content-Type") == "image/png" and image.read(8) == b"\x89PNG\r\n\x1a\n"
        except HTTPError:
            cite["accessible"] = False
    return {"id": case, "question": question, "http": code, "segundos_post": elapsed, **row}



def trace_query(question, corpus, catalog):
    from dataclasses import asdict
    from math import ceil

    from apps.api.corpus import SearchRequest, definition_source, definition_topic, documentary_query, explanation_terms, terms
    from apps.api.finance import Abstain, check_stock_sum
    from apps.api.financial_agent import parse_intent, requires_financial_tools
    from apps.api.financial_evidence import find_candidates

    def pages(refs):
        return [[catalog[ref.doc_id], ref.pdf_page] for ref in refs]

    if requires_financial_tools(question):
        try:
            intent = parse_intent(question)
        except Abstain as error:
            return {"ruta": "financiera", "motivo": str(error), "candidatos": {}}
        try:
            check_stock_sum(intent.operation, intent.metric)
        except Abstain as error:
            return {"ruta": "financiera", "intención": asdict(intent), "motivo": str(error), "candidatos": {}}
        return {"ruta": "financiera", "intención": asdict(intent), "candidatos": {
            intent.base.label: pages(find_candidates(corpus, intent.metric, intent.base, intent.current)),
            intent.current.label: pages(find_candidates(corpus, intent.metric, intent.current, intent.base)),
        }}
    query = documentary_query(question)
    topic = definition_topic(query)
    source = definition_source(query) if topic else set()
    explanation = explanation_terms(query) if not topic else set()
    tokens = [token for token in terms(topic if source else query) if not explanation or token in explanation][:18]
    return {"ruta": "documental", "consulta": query, "tema": topic, "emisor": sorted(source),
            "términos_fts": tokens, "mínimo": ceil(0.8 * len(tokens)),
            "candidatos": pages(corpus.search_corpus(SearchRequest(query=question)))}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--data", type=Path, required=True)
    cli.add_argument("--base", default="http://127.0.0.1:5194")
    cli.add_argument("--recorded", type=Path)
    cli.add_argument("--trace-state", type=Path, help="Incluye la traza local con un índice ya existente")
    suite = cli.add_mutually_exclusive_group()
    suite.add_argument("--paraphrases", action="store_true", help="Incluye cuatro variantes de D02 y una de D03")
    suite.add_argument("--operations", action="store_true", help="Consulta la muestra de generalización y sus negativos")
    args = cli.parse_args()
    questions = {**QUESTIONS, **PARAPHRASES} if args.paraphrases else QUESTIONS
    if args.operations:
        questions = OPERATIONS
    root = args.data.resolve(strict=True)
    endpoint = urlparse(args.base)
    if endpoint.scheme != "http" or not ip_address(endpoint.hostname or "").is_loopback or endpoint.path or endpoint.username:
        cli.error("La evaluación admite únicamente el servicio HTTP local de loopback.")
    if args.recorded:
        rows = [json.loads(line) for line in args.recorded.read_text().splitlines()]
        if [(row["id"], row["question"]) for row in rows] != list(questions.items()):
            cli.error("La captura no coincide con las preguntas de la evaluación.")
    else:
        rows = (live(args.base, case, question) for case, question in questions.items())
    corpus = None
    if args.trace_state:
        from apps.api.corpus import Corpus

        if not (args.trace_state / "corpus.sqlite3").is_file():
            cli.error("La traza requiere un índice SQLite existente.")
        corpus = Corpus(root, args.trace_state)
        catalog = {document["doc_id"]: document["filename"] for document in corpus.catalog()}

    passed = True
    for row in rows:
        result = assess(root, row)
        if corpus:
            result["traza"] = trace_query(row["question"], corpus, catalog)
        passed &= result["veredicto"] == "PASS"
        print(json.dumps(result, ensure_ascii=False), flush=True)
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
