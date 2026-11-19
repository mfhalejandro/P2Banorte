# Sprint P0 · Consulta con evidencia

**Verificado técnicamente · 2026-11-19.** Entrada: aprobación funcional del PRD V3 y de [SPEC-001 v2](../../specs/SPEC-001-cita-pdf.md). Responsable de ejecución previsto: agente de desarrollo. El propietario decide la aceptación funcional. La aprobación del solicitante abre el sprint. [Plan del corte](../../plans/implementation-spec-001-p0.md)

| Tarea | Dependencia | Criterios SPEC-001 | Estado / evidencia |
|---|---|---|---|
| P0-01 · PDF a índice | Aprobación | AC-04 | Ejecutada. T-01/T-02 y doble ingesta real: PASS |
| P0-02 · Búsqueda a respuesta | P0-01 | AC-03/05/06 | Ejecutada. FTS, abstención, procedencia y límites de proveedor: PASS |
| P0-03 · API, chat, cita y visor | Contrato de spec para UI, P0-02 para integración | AC-01/02/06 | Ejecutada. API, imagen del original y cinco viewports: PASS |
| P0-04 · Recorrido completo reproducible | P0-01 a P0-03 | AC-01 a AC-06 | Ejecutada. Smoke real a 375 px con cotejo de página: PASS |
