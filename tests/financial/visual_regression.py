"""Preguntas literales y criterios de la revisión visual en el navegador."""

ANNUAL = "IA Banorte ESP_16.pdf"
FINANCIALS = "EEFF 2025 Grupo_.pdf"
QUARTER = "3T24.pdf"
MARKET = "2T24.pdf"
PERIMETER = "3T25_vc.pdf"
VISUAL = {
    "D01": (
        "¿Cómo se define el riesgo de crédito en los informes de Banorte? Indica el documento y la página donde aparece la definición.",
        "answered", ("pérdida potencial", "falta de pago"),
        ((ANNUAL, 29, "La pérdida potencial por la falta de pago de un acreditado"),),
    ),
    "D02": (
        "¿Cuáles son las principales políticas de riesgo de balance y liquidez de la Tenedora? Preséntalas en una lista e indica su fuente.",
        "answered", ("Límites Globales y Específicos", "medición y monitoreo", "información y revelación", "parcial"),
        ((FINANCIALS, 152, "Las políticas de Riesgo de Liquidez en la Tenedora contemplan"),),
    ),
    "D03": (
        "¿Cómo se define el Coeficiente de Cobertura de Liquidez en los informes de la Tenedora?",
        "answered", ("activos líquidos", "salidas netas de efectivo", "30 días", "estrés regulatorio"),
        ((FINANCIALS, 153, "relación entre Activos Líquidos y Salidas Netas de Efectivo"),),
    ),
    "D04": (
        "Del informe anual de Banorte, señala los dos segmentos del portafolio de crédito y, por separado, los controles de originación.",
        "answered", ("minorista", "mayorista", "identificación exhaustiva", "validación robusta"),
        ((ANNUAL, 29, "segmentamos nuestro portafolio"), (ANNUAL, 30, "Identificación exhaustiva del cliente")),
    ),
    "D05": (
        "En la gestión de liquidez de la Tenedora, ¿a quién se informa semanalmente y a quién se informa trimestralmente?",
        "answered", ("semanales al grupo de gestión de capital y liquidez", "trimestral al Consejo"),
        ((FINANCIALS, 153, "semanales al grupo de gestión de capital y liquidez"),),
    ),
    "D06": (
        "¿Se pueden atribuir a todas las filiales las políticas de la Tenedora que aparecen en el capítulo de liquidez de los estados financieros de 2025?",
        "answered", ("no acredita",),
        ((FINANCIALS, 152, "Las políticas de Riesgo de Liquidez en la Tenedora contemplan"),),
    ),
    "F01": (
        "Tomando como base el segundo trimestre de 2024, determina cuánto creció porcentualmente la utilidad neta trimestral de GFNorte al tercer trimestre de ese año. Incluye las dos cifras originales y su procedencia.",
        "answered", ("14,018", "14,238", "220 millones de pesos", "1.57 %"), ((QUARTER, 5, "Utilidad Neta"),),
    ),
    "F02": (
        "Al contrastar el ROE de GFNorte del 3T24 con el del 2T25, ¿cuántos puntos porcentuales varió? Comprueba también que la definición del indicador sea comparable.",
        "answered", ("22.9%", "23.6%", "0.7 puntos porcentuales", "misma definición"),
        (("4T24_1.pdf", 6, "ROE (2)"), ("2T25_vc_.pdf", 6, "ROE (2)")),
    ),
    "F03": (
        "En la tabla bursátil del segundo trimestre de 2024, ¿cuánto cayó la capitalización de mercado de GFNorte respecto al primer trimestre, tanto en MXN como en USD? Presenta los dos cálculos por separado.",
        "answered", ("508,555", "406,931", "-101624 millones de pesos", "30,761", "22,300", "-8461 millones de dólares"),
        ((MARKET, 7, "Capitalización de Mercado"),),
    ),
    "F04": (
        "¿Qué fracción porcentual representa la utilidad neta del 3T24 dentro del acumulado 9M24?",
        "answered", ("14,238", "42,464", "33.53 % de participación", "no son equivalentes"),
        ((QUARTER, 5, "Utilidad Neta"),),
    ),
    "F05": (
        "¿En cuánto cambió el ROA de GFNorte entre 3T23 y 3T24? Indica también el cambio del ROE en esos trimestres.",
        "answered", ("2.3%", "2.4%", "0.1 puntos porcentuales", "21.5%", "22.9%", "1.4 puntos porcentuales"),
        ((QUARTER, 6, "ROA (3)"), (QUARTER, 6, "ROE (2)")),
    ),
    "F06": (
        "¿Cuánto varió la utilidad neta de GFNorte del 2T24 al 3T24? Dame además el cambio del ROE en esos trimestres.",
        "answered", ("14,018", "14,238", "220 millones de pesos", "23.3%", "22.9%", "-0.4 puntos porcentuales"),
        ((QUARTER, 5, "Utilidad Neta"), (QUARTER, 6, "ROE (2)")),
    ),
    "F07": (
        "Para la utilidad neta de GFNorte entre 3T23 y 3T24, calcula la diferencia absoluta y la variación relativa.",
        "answered", ("13,268", "14,238", "970 millones de pesos", "7.31 %"), ((QUARTER, 5, "Utilidad Neta"),),
    ),
    "F08": (
        "¿Cuánto se redujo la capitalización de mercado en pesos entre el primer trimestre de 2024 y el segundo trimestre de ese año?",
        "answered", ("508,555", "406,931", "-101624 millones de pesos"), ((MARKET, 7, "Capitalización de Mercado"),),
    ),
    "S01": (
        "Compara la utilidad neta de GFNorte de 3T23 a 3T24, expresada exclusivamente en francos suizos.",
        "abstained", ("moneda",), (),
    ),
    "S02": (
        "Para obtener una cifra anual más grande, suma los activos totales de GFNorte al cierre de 1T24 y 2T24 y presenta el total.",
        "abstained", ("saldo a una fecha de corte", "no es aditiva"), (),
    ),
    "S03": ("Compara el ROA de Banco Nébula entre 3T23 y 3T24.", "abstained", ("entidad",), ()),
    "S04": ("¿Qué exigencia de liquidez aprobó la Tenedora para el ejercicio 2043?", "abstained", ("evidencia suficiente",), ()),
    "S05": (
        "¿Se puede afirmar que la utilidad neta de GFNorte tuvo una variación directamente comparable entre 3T24 y 3T25? Explica qué efecto tiene Bineo y muestra las evidencias relevantes.",
        "abstained", ("Bineo", "sin base común verificada"),
        ((PERIMETER, 5, "no son comparables con aquellas presentadas en los periodos respectivos"),),
    ),
    "S06": (
        "¿Qué porcentaje representa la utilidad neta de 4T25 respecto de 9M25 en una participación del acumulado?",
        "abstained", ("no está incluido",), (),
    ),
}

VISUAL_OPERANDS = {
    "F01": {("Utilidad Neta", "2T24", "14,018"), ("Utilidad Neta", "3T24", "14,238")},
    "F02": {("ROE (2)", "3T24", "22.9%"), ("ROE (2)", "2T25", "23.6%")},
    "F03": {("Capitalización de Mercado (Millones de pesos)", "1T24", "508,555"),
            ("Capitalización de Mercado (Millones de pesos)", "2T24", "406,931"),
            ("Capitalización de Mercado (Millones de dólares)", "1T24", "30,761"),
            ("Capitalización de Mercado (Millones de dólares)", "2T24", "22,300")},
    "F04": {("Utilidad Neta", "3T24", "14,238"), ("Utilidad Neta", "9M24", "42,464")},
    "F05": {("ROA (3)", "3T23", "2.3%"), ("ROA (3)", "3T24", "2.4%"),
            ("ROE (2)", "3T23", "21.5%"), ("ROE (2)", "3T24", "22.9%")},
    "F06": {("Utilidad Neta", "2T24", "14,018"), ("Utilidad Neta", "3T24", "14,238"),
            ("ROE (2)", "2T24", "23.3%"), ("ROE (2)", "3T24", "22.9%")},
    "F07": {("Utilidad Neta", "3T23", "13,268"), ("Utilidad Neta", "3T24", "14,238")},
    "F08": {("Capitalización de Mercado (Millones de pesos)", "1T24", "508,555"),
            ("Capitalización de Mercado (Millones de pesos)", "2T24", "406,931")},
}

OBSERVED = {
    "D01": "PASS", "D02": "PASS", "D03": "FAIL", "D04": "FAIL", "D05": "FAIL", "D06": "FAIL",
    "F01": "PASS", "F02": "PASS", "F03": "PASS", "F04": "PASS", "F05": "FAIL", "F06": "PARTIAL",
    "F07": "PASS", "F08": "FAIL",
    "S01": "PASS", "S02": "PASS", "S03": "PASS", "S04": "PASS", "S05": "PASS", "S06": "PARTIAL",
}

# Cada entrada debe aparecer en la propia cita, además de estar en el PDF.
DOCUMENTARY_EVIDENCE = {
    "D01": [(ANNUAL, 29, ("pérdida potencial", "falta de pago"))],
    "D02": [(FINANCIALS, 152, ("Límites Globales y Específicos", "medición y monitoreo", "información y revelación"))],
    "D03": [(FINANCIALS, 153, ("activos líquidos", "salidas netas de efectivo", "30 días", "estrés regulatorio"))],
    "D04": [(ANNUAL, 29, ("minorista", "mayorista")), (ANNUAL, 30, ("identificación exhaustiva", "validación robusta"))],
    "D05": [(FINANCIALS, 153, ("semanales al grupo de gestión de capital y liquidez", "trimestral al Consejo"))],
    "D06": [(FINANCIALS, 152, ("Las políticas de Riesgo de Liquidez en la Tenedora contemplan",))],
    "S05": [(PERIMETER, 5, ("Bineo", "no son comparables"))],
}
