"""Aceptación dirigida del corpus de ensayo. Lectura local, sin ingesta."""
import argparse
from decimal import Decimal
from hashlib import sha256
from ipaddress import ip_address
import json
from pathlib import Path
import re
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
    case = row["id"][:3]
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
    elif case == "F03" and status == "abstained" and not evidence and not tools and contains(answer, "dos periodos distintos"):
        verdict, reason = "PASS", "Pide los periodos antes de consultar el corpus."
    return {**row, "veredicto": verdict, "justificación": reason, "validación_citas": evidence}


def live(base, case, question):
    request = Request(base + "/api/chat", data=json.dumps({"message": question}).encode(),
                      headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=35) as resp:
            code, row = resp.status, json.load(resp)
    except HTTPError as exc:
        code = exc.code
        row = {"answer": "HTTP " + str(code), "status": None, "provider_mode": None, "tools_used": [], "citations": []}
    for cite in row["citations"]:
        url = f'{base}/api/documents/{cite["doc_id"]}/pages/{cite["pdf_page"]}/image'
        try:
            with urlopen(url, timeout=25) as image:
                cite["accessible"] = image.getheader("Content-Type") == "image/png" and image.read(8) == b"\x89PNG\r\n\x1a\n"
        except HTTPError:
            cite["accessible"] = False
    return {"id": case, "question": question, "http": code, **row}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--data", type=Path, required=True)
    cli.add_argument("--base", default="http://127.0.0.1:5194")
    cli.add_argument("--recorded", type=Path)
    cli.add_argument("--paraphrases", action="store_true", help="Incluye cuatro variantes de D02 y una de D03")
    args = cli.parse_args()
    questions = {**QUESTIONS, **PARAPHRASES} if args.paraphrases else QUESTIONS
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
    passed = True
    for row in rows:
        result = assess(root, row)
        passed &= result["veredicto"] == "PASS"
        print(json.dumps(result, ensure_ascii=False), flush=True)
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
