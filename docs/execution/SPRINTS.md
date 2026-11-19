# Sprint P0 · Consulta con evidencia

**Verificado técnicamente · 2026-11-19.** Entrada: aprobación funcional del PRD V3 y de [SPEC-001 v2](../../specs/SPEC-001-cita-pdf.md). Responsable de ejecución previsto: agente de desarrollo. El propietario decide la aceptación funcional. La aprobación del solicitante abre el sprint. [Plan del corte](../../plans/implementation-spec-001-p0.md)

| Tarea | Dependencia | Criterios SPEC-001 | Estado / evidencia |
|---|---|---|---|
| P0-01 · PDF a índice | Aprobación | AC-04 | Ejecutada. T-01/T-02 y doble ingesta real: PASS |
| P0-02 · Búsqueda a respuesta | P0-01 | AC-03/05/06 | Ejecutada. FTS, abstención, procedencia y límites de proveedor: PASS |
| P0-03 · API, chat, cita y visor | Contrato de spec para UI, P0-02 para integración | AC-01/02/06 | Ejecutada. API, imagen del original y cinco viewports: PASS |
| P0-04 · Recorrido completo reproducible | P0-01 a P0-03 | AC-01 a AC-06 | Ejecutada. Smoke real a 375 px con cotejo de página: PASS |

## Sprint financiero · SPEC-002 local

| Tarea | Criterio | Responsable | Estado |
|---|---|---|---|
| F-01 · Procedencia y Decimal | AC-03 | Codex | PASS, oráculos y errores Decimal |
| F-02 · Periodos, tablas y citas | AC-02 | Codex | PASS, dos citas y prueba de tabla |
| F-03 · Orquestación con doble y P0 | AC-01/05 | Codex | PASS, doble y compatibilidad P0 |
| F-04 · Corpus y demo | AC-04 | Codex | PASS, ensayo 2 → 8 → 24 PDF |

AC-06 queda pendiente de autorización independiente. [Plan](../../plans/implementation-spec-002-financiero.md)

### Cierre dirigido de robustez

| Tarea | Evidencia | Estado |
|---|---|---|
| Cierre R08/R09 · asociación moneda, fila y periodo | Dos cálculos reales exactos y cuatro citas. Dos layouts sintéticos y rechazo de ambigüedad | VERIFIED |
| Cierre R14 · saldo de cierre | Abstención motivada antes de consultar el catálogo, con regresión sintética | VERIFIED |
| Regresión P0 y SPEC-002 local | 14/14 de la muestra, 25/25 PNG y 6 pruebas en Chromium. Los otros 11 casos mantuvieron respuesta y citas | VERIFIED |
| Cobertura de otros layouts y publicación del cierre | Persisten límites fuera de la muestra y la publicación depende de autorización | PARTIAL |
| Inferencia generativa real · AC-06 | Autorización independiente pendiente | NOT RUN |

[Informe de robustez](../quality/ROBUSTEZ_CORPUS_2026-11-19.md)
