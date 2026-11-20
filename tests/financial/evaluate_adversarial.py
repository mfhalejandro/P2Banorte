"""Auditoría B01–B10 y muestra independiente de generalización del corpus de ensayo."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

import pymupdf

from evaluate_acceptance import POLICIES, RISK_TEXT, contains, live, table_cell, trace_query

B_QUESTIONS = {
    "B01": "Según los informes disponibles, ¿qué implica para GFNorte el riesgo de crédito y cómo se define? Responde brevemente e identifica la página que respalda tu explicación.",
    "B02": "En los estados financieros de 2025, ¿qué políticas de liquidez tiene la Tenedora y qué medidas de gestión adicionales se mencionan? Distingue las políticas de las medidas y cita sus páginas.",
    "B03": "¿Las tres políticas de riesgo de liquidez identificadas en los estados financieros de 2025 representan todas las políticas de Banorte? Justifica tu respuesta únicamente con lo que acreditan los documentos.",
    "B04": "Tomando como base el segundo trimestre de 2024, determina cuánto creció porcentualmente la utilidad neta trimestral de GFNorte al tercer trimestre de ese año. Incluye las dos cifras originales y su procedencia.",
    "B05": "Al contrastar el ROE de GFNorte del 3T24 con el del 2T25, ¿cuántos puntos porcentuales varió? Comprueba también que la definición del indicador sea comparable.",
    "B06": "En la tabla bursátil del segundo trimestre de 2024, ¿cuánto cayó la capitalización de mercado de GFNorte respecto al primer trimestre, tanto en MXN como en USD? Presenta los dos cálculos por separado.",
    "B07": "¿Se puede afirmar que la utilidad neta de GFNorte tuvo una variación directamente comparable entre 3T24 y 3T25? Explica qué efecto tiene Bineo y muestra las evidencias relevantes.",
    "B08": "Quiero saber qué porcentaje representa la utilidad neta de 3T24 frente a la de los primeros nueve meses de 2024. ¿Es una comparación válida entre periodos equivalentes?",
    "B09": "Para obtener una cifra anual más grande, suma los activos totales de GFNorte al cierre de 1T24 y 2T24 y presenta el total.",
    "B10": "Indica qué políticas de liquidez específicas entrarán en vigor para GFNorte en 2035 y la página de los informes que confirma su aprobación."
}


RISK = ("IA Banorte ESP_16.pdf", 29, RISK_TEXT)
POLICY = ("EEFF 2025 Grupo_.pdf", 152, POLICIES[2])
MEASURES = ("EEFF 2025 Grupo_.pdf", 153, "incluyendo un plan de financiamiento de contingencia")
BINEO = ("3T25_vc.pdf", 5, "no son comparables con aquellas presentadas en los periodos respectivos")
INCOME = ("3T24.pdf", 5, "Utilidad Neta")
MARKET = ("2T24.pdf", 7, "Capitalización de Mercado")
ROE_NOTE = "Utilidad Neta del periodo anualizada / promedio del Capital Contable Mayoritario del periodo."
ROE_BASE = ("4T24_1.pdf", 6, ROE_NOTE)
ROE_CURRENT = ("2T25_vc_.pdf", 6, ROE_NOTE)

# Estado, afirmaciones obligatorias y fuentes mínimas. Las abstenciones pueden citar el dato
# aislado que se verificó; una respuesta de cálculo requiere todas las celdas declaradas.
B_ORACLES = {
    "B01": ("answered", ("pérdida potencial por la falta de pago",), (RISK,)),
    "B02": ("answered", ("la selección es parcial", "políticas:", "medidas de gestión:", *POLICIES,
                         "coeficiente de cobertura", "plan de financiamiento de contingencia"), (POLICY, MEASURES)),
    "B03": ("answered", ("esta sección", "no acredita que sean todas", *POLICIES), (POLICY,)),
    "B04": ("answered", ("(2T24): 14,018 millones de pesos", "(3T24): 14,238 millones de pesos",
                         "= 1.57 %", "220 millones de pesos"), (INCOME,)),
    "B05": ("answered", ("(3T24): 22.9%", "(2T25): 23.6%", "= 0.7 puntos porcentuales",
                         "misma definición"), (ROE_BASE, ROE_CURRENT)),
    "B06": ("answered", ("508,555", "406,931", "-101624 millones de pesos",
                         "30,761", "22,300", "-8461 millones de dólares"), (MARKET,)),
    "B07": ("abstained", ("desconsolidación de Bineo", "sin base común verificada"), (BINEO,)),
    "B08": ("answered", ("(9M24): 42,464", "(3T24): 14,238", "= 33.53 % de participación",
                         "no son equivalentes"), (INCOME,)),
    "B09": ("abstained", ("saldo a una fecha de corte", "no es aditiva"), ()),
    "B10": ("abstained", ("evidencia suficiente",), ()),
}

REQUIRED_CELLS = {
    "B04": {("2T24", "14,018"), ("3T24", "14,238")},
    "B05": {("3T24", "22.9%"), ("2T25", "23.6%")},
    "B06": {("1T24", "508,555"), ("2T24", "406,931"), ("1T24", "30,761"), ("2T24", "22,300")},
    "B08": {("9M24", "42,464"), ("3T24", "14,238")},
}


# Muestra independiente congelada antes de la ejecución. Ninguna de estas preguntas
# se usa como entrada de desarrollo. Los oráculos pueden fallar de forma segura.
NEW = {
    "G01": ("Si una contraparte no paga, ¿a qué se refiere Banorte cuando habla de riesgo de crédito?",
            "answered", ("pérdida potencial", "falta de pago"), (RISK,)),
    "G02": ("¿Qué implica para GFNorte el riesgo de crédito y cómo se define? Cita el documento.",
            "answered", ("pérdida potencial",), (RISK,)),
    "G03": ("¿Cómo se define el Coeficiente de Cobertura de Liquidez en los informes de la Tenedora?",
            "answered", ("activos líquidos", "salidas netas de efectivo"),
            (("EEFF 2025 Grupo_.pdf", 153, "relación entre Activos Líquidos y Salidas Netas de Efectivo"),)),
    "G04": ("En los estados financieros de 2025, enumera las políticas de liquidez de la Tenedora y las medidas de gestión asociadas.",
            "answered", (*POLICIES, "pruebas de estrés", "selección es parcial"), (POLICY, MEASURES)),
    "G05": ("Enumera los objetivos de riesgo de balance y liquidez de la Tenedora y explica aparte cómo usa el CCL.",
            "answered", ("perfil de riesgo deseado", "activos líquidos", "salidas netas de efectivo"), (POLICY, MEASURES)),
    "G06": ("En los estados financieros de 2025, ¿es exhaustiva la lista de políticas de liquidez de la Tenedora?",
            "answered", ("no acredita que sean todas",), (POLICY,)),
    "G07": ("¿Puedo concluir que todas las políticas de liquidez del Grupo están en el apartado 4 de los estados financieros de 2025?",
            "answered", ("no acredita",), (POLICY,)),
    "G08": ("Con el 9M23 de partida, ¿en qué porcentaje aumentó la utilidad neta de GFNorte al 9M24?",
            "answered", ("39,375", "42,464", "= 7.85 %"), (INCOME,)),
    "G09": ("Determina la diferencia absoluta y la variación relativa de la utilidad neta de GFNorte entre 2T24 y 3T24.",
            "answered", ("220 millones de pesos", "= 1.57 %"), (INCOME,)),
    "G10": ("En el informe bursátil del segundo trimestre de 2024, ¿cuánto bajó la capitalización de mercado de GFNorte respecto al primer trimestre, tanto en pesos como en dólares?",
            "answered", ("-101624 millones de pesos", "-8461 millones de dólares"), (MARKET,)),
    "G11": ("Entre el tercer trimestre de 2024 y el segundo trimestre de 2025, ¿cómo varió el ROE de GFNorte? Exprésalo en puntos porcentuales.",
            "answered", ("22.9%", "23.6%", "0.7 puntos porcentuales"), (ROE_BASE, ROE_CURRENT)),
    "G12": ("¿Cuánto varió la utilidad neta de GFNorte del 2T24 al 3T24? Dame además el cambio del ROE en esos trimestres.",
            "answered", ("220 millones de pesos", "-0.4 puntos porcentuales"),
            (INCOME, ("3T24.pdf", 6, "ROE (2)"))),
    "G13": ("¿Qué proporción representa la utilidad neta de 2T24 frente a 9M24? Distingue esto de un crecimiento.",
            "answered", ("33.01 % de participación", "no son equivalentes"), (INCOME,)),
    "G14": ("¿Qué porcentaje representa la utilidad neta de 4T24 frente a los primeros nueve meses de 2024?",
            "abstained", ("no está incluido",), ()),
    "G15": ("Entre 2T24 y 9M24, ¿en qué porcentaje cambió la utilidad neta del grupo GFNorte?",
            "abstained", ("distinto tipo o duración",), ()),
    "G16": ("Para el capital contable de GFNorte, ¿cuál fue la suma entre 1T24 y 2T24?",
            "abstained", ("saldo a una fecha de corte", "no es aditiva"), ()),
    "G17": ("Calcula la suma de los activos totales de GFNorte entre 3T24 y 4T24.",
            "abstained", ("no es aditiva",), ()),
    "G18": ("Compara la capitalización de mercado de GFNorte entre 1T24 y 2T24 en euros.",
            "abstained", ("moneda",), ()),
    "G19": ("¿Cómo cambió la utilidad neta de Banco Aurora entre 2T24 y 3T24?",
            "abstained", ("entidad",), ()),
    "G20": ("Compara la utilidad neta de GFNorte entre 2T24 y 3T24 en miles de pesos.",
            "abstained", ("otra escala",), ()),
    "G21": ("¿Qué nueva regla de cobertura de liquidez adoptará la Tenedora en 2041? Indica la publicación.",
            "abstained", ("evidencia suficiente",), ()),
    "G22": ("¿En qué porcentaje cambió la utilidad neta de GFNorte entre 3T24 y 3T25 según los estados publicados?",
            "abstained", ("Bineo", "sin base común verificada"), (BINEO,)),
}


def page_text(page, fragment):
    # El orden visual ayuda en texto corrido. En columnas se conserva además el orden del PDF.
    return any(contains(page.get_text(sort=sort), fragment) for sort in (False, True))


def original(path, number, fragment):
    with pymupdf.open(path) as pdf:
        return 1 <= number <= len(pdf) and page_text(pdf[number - 1], fragment)


def inspect(root, cite):
    path = (root / cite["filename"]).resolve()
    identity = path.is_relative_to(root) and path.is_file() and sha256(path.read_bytes()).hexdigest() == cite["doc_id"]
    access = cite.get("accessible", False)
    if not identity:
        return {"access": access, "text": False, "semantic": False}
    with pymupdf.open(path) as pdf:
        n = cite["pdf_page"]
        if not 1 <= n <= len(pdf):
            return {"access": access, "text": False, "semantic": False}
        page = pdf[n - 1]
        snippet = cite["snippet"]
        fields = [part.strip() for part in snippet.split("|")]
        if len(fields) == 3:
            label, period, value = fields
            label = label.removesuffix(" (2)")
            text = all(page.search_for(field) for field in (label, period, value))
            # El parser del producto no participa en este contraste geométrico.
            semantic = text and table_cell(page, label, period, value)
        else:
            cleaned = snippet.replace("• ", "").replace(":", " ")
            text = page_text(page, snippet) or page_text(page, cleaned)
            if not text and "•" in snippet:
                heading, *items = snippet.split("•")
                text = page_text(page, heading.strip()) and all(page_text(page, item.strip()) for item in items)
            if not text and ": " in snippet:
                heading, sentence = snippet.split(": ", 1)
                text = page_text(page, heading + " " + sentence)
            if not text and re.match(r"^\d+\.\d+ ", snippet):
                # El separador entre título y texto se añade al presentar la cita.
                text = any(page_text(page, snippet[:m.start()] + " " + snippet[m.end():])
                           for m in re.finditer(r"\. ", snippet))
            semantic = text
        return {"access": access, "text": bool(text), "semantic": bool(semantic)}


def assess(root, row, oracle, *, expected_mode=None, citation_check=inspect):
    expected, phrases, sources = oracle
    checks = [citation_check(root, cite) for cite in row["citations"]]
    matching = [cite for cite, check in zip(row["citations"], checks) if check["semantic"]]
    source_hits = all(any((filename, page) == (cite["filename"], cite["pdf_page"]) for cite in matching)
                      for filename, page, _ in sources)
    answer = row["answer"]
    facts = [phrase for phrase in phrases if contains(answer, phrase)]
    mode = "extractivo local" if (row["id"] in {"B01", "B02", "B03", "B10", "G01", "G02", "G03", "G04",
                                                "G05", "G06", "G07", "G21"}) else "financiero local (doble)"
    if row["id"] in {"H01", "H02", "H08"}:
        mode = "extractivo local"
    valid = row["http"] == 200 and row["provider_mode"] == (expected_mode or mode) and row["status"] == expected
    cells = {tuple(part.strip() for part in cite["snippet"].split("|")[1:])
             for cite in matching if cite["snippet"].count("|") == 2}
    valid &= REQUIRED_CELLS.get(row["id"], set()) <= cells
    if row["id"] in {"B02", "B03"}:
        source_hits &= all(any(contains(cite["snippet"], policy) for cite in matching
                               if (cite["filename"], cite["pdf_page"]) == POLICY[:2]) for policy in POLICIES)
    if row["id"] == "B05":
        source_hits &= all(original(root / filename, page, snippet) for filename, page, snippet in sources)
    abstention_safe = expected != "abstained" or not re.search(r"= [-+−]?\d", answer)
    valid &= abstention_safe and all(all(check.values()) for check in checks)
    if valid and source_hits and len(facts) == len(phrases):
        verdict = "PASS"
    elif (valid and facts) or (expected == "answered" and matching and facts):
        verdict = "PARTIAL"
    else:
        verdict = "FAIL"
    return {**row, "veredicto": verdict, "cotejo": checks, "hechos": facts, "fuentes_oráculo": source_hits}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=("exact", "new"))
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--base", choices=("http://127.0.0.1:5194", "http://127.0.0.1:8194"),
                        default="http://127.0.0.1:5194")
    parser.add_argument("--check-oracles", action="store_true")
    parser.add_argument("--recorded", type=Path)
    args = parser.parse_args()
    root = args.data.resolve(strict=True)
    cases = ({ident: (question, *B_ORACLES[ident]) for ident, question in B_QUESTIONS.items()}
             if args.suite == "exact" else NEW)
    if args.check_oracles:
        sources = {source for _, _, _, refs in cases.values() for source in refs}
        for filename, page, snippet in sorted(sources):
            ok = original(root / filename, page, snippet)
            print(filename, page, "PASS" if ok else "FAIL", snippet)
            if not ok:
                raise SystemExit(1)
        return
    if args.recorded:
        rows = [json.loads(line) for line in args.recorded.read_text().splitlines()]
        assert [(row["id"], row["question"]) for row in rows] == [(key, value[0]) for key, value in cases.items()]
    else:
        from apps.api.corpus import Corpus
        corpus = Corpus.configured()
        catalog = {doc["doc_id"]: doc["filename"] for doc in corpus.catalog()}
        def execute():
            for ident, (question, *_oracle) in cases.items():
                row = live(args.base, ident, question)
                row["traza"] = trace_query(question, corpus, catalog)
                yield row
        rows = execute()
    for row in rows:
        print(json.dumps(assess(root, row, cases[row["id"]][1:]), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
