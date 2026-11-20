"""Muestra exploratoria K. Verificar los oráculos contra los PDF antes de medir."""
ANNUAL = "IA Banorte ESP_16.pdf"
LIQUIDITY = "EEFF 2025 Grupo_.pdf"
PERIMETER = ("3T25_vc.pdf", 5, "no son comparables con aquellas presentadas en los periodos respectivos")
K = {
    "K01": ("Si un acreditado deja de pagar, ¿qué pérdida potencial incluye Banorte dentro del riesgo de crédito?",
            "answered", ("falta de pago de un acreditado", "garantías otorgadas"),
            ((ANNUAL, 29, "La pérdida potencial por la falta de pago de un acreditado"),)),
    "K02": ("En los estados financieros de 2025, ¿qué relación mide la cobertura de liquidez de la Tenedora bajo estrés regulatorio?",
            "answered", ("activos líquidos", "salidas netas de efectivo", "30 días"),
            ((LIQUIDITY, 153, "relación entre Activos Líquidos y Salidas Netas de Efectivo"),)),
    "K03": ("Del informe anual de Banorte, señala los dos segmentos del portafolio de crédito y, por separado, los controles de originación.",
            "answered", ("minorista", "mayorista", "identificación exhaustiva", "validación robusta"),
            ((ANNUAL, 29, "segmentamos nuestro portafolio"), (ANNUAL, 30, "Identificación exhaustiva del cliente"))),
    "K04": ("En la gestión de liquidez de la Tenedora, ¿a quién se informa semanalmente y a quién se informa trimestralmente?",
            "answered", ("semanales al grupo de gestión de capital y liquidez", "trimestral al Consejo"),
            ((LIQUIDITY, 153, "semanales al grupo de gestión de capital y liquidez"),)),
    "K05": ("¿Cuánto se movió el ROE de GFNorte del tercer trimestre de 2023 al tercer trimestre del año siguiente?",
            "answered", ("21.5%", "22.9%", "1.4 puntos porcentuales"), (("3T24.pdf", 6, "ROE (2)"),)),
    "K06": ("¿Qué fracción porcentual representa la utilidad neta del 3T24 dentro del acumulado 9M24?",
            "answered", ("14,238", "42,464", "33.53 %"), (("3T24.pdf", 5, "Utilidad Neta"),)),
    "K07": ("Para la utilidad neta de GFNorte entre 3T23 y 3T24, calcula la diferencia absoluta y la variación relativa.",
            "answered", ("13,268", "14,238", "970 millones de pesos", "7.31 %"), (("3T24.pdf", 5, "Utilidad Neta"),)),
    "K08": ("¿Cuánto se redujo la capitalización de mercado en pesos entre el primer trimestre de 2024 y el segundo trimestre de ese año?",
            "answered", ("508,555", "406,931", "-101624 millones de pesos"), (("2T24.pdf", 7, "Capitalización de Mercado"),)),
    "K09": ("Compara la utilidad neta de GFNorte de 2T24 a 3T24. Usa solo dólares canadienses.",
            "abstained", ("moneda",), ()),
    "K10": ("¿Cuál es la suma del capital contable de GFNorte al cierre de 2T24 y de 3T24?",
            "abstained", ("no es aditiva",), ()),
    "K11": ("Compara el ROE de Banco Cometa entre 2T24 y 3T24.",
            "abstained", ("entidad",), ()),
    "K12": ("¿En cuánto cambió la utilidad neta de GFNorte de 1T24 a 3T25? Cita cualquier reserva sobre la base comparable.",
            "abstained", ("Bineo", "sin base común verificada"), (PERIMETER,)),
}

K_OPERANDS = {
    "K05": {("ROE (2)", "3T23", "21.5%"), ("ROE (2)", "3T24", "22.9%")},
    "K06": {("Utilidad Neta", "3T24", "14,238"), ("Utilidad Neta", "9M24", "42,464")},
    "K07": {("Utilidad Neta", "3T23", "13,268"), ("Utilidad Neta", "3T24", "14,238")},
    "K08": {("Capitalización de Mercado (Millones de pesos)", "1T24", "508,555"),
            ("Capitalización de Mercado (Millones de pesos)", "2T24", "406,931")},
}
