# Estado del proyecto

**P0 · aplicación V3.** El solicitante aprobó el PRD de la entrega confirmada y [SPEC-001 v2](../../specs/SPEC-001-cita-pdf.md). El primer corte integra lectura de PDF, FTS5/BM25, agente extractivo local, FastAPI, chat y visor de originales. Las instrucciones reproducibles están en el [README](../../README.md).

El registro de [tareas](SPRINTS.md) y la [bitácora](EXECUTION_LOG.md) identifican las pruebas realizadas. La autorización de entrega cubre CI y el P0 verificado en `main`. Las fuentes RCTF siguen en el entorno protegido. El modo con proveedor generativo externo requiere autorización de destino y un contrato de inferencia disponible.

**SPEC-002 · corte financiero local implementado.** El modo `financial-local` comparte el índice y el visor del P0. El responsable verificó AC-01 a AC-05 con doble, pruebas de oráculos y comparación de evidencia real. AC-06 permanece NOT RUN, pendiente de autorización independiente. [Plan](../../plans/implementation-spec-002-financiero.md) · [Bitácora](EXECUTION_LOG.md)

**Robustez sobre el ensayo de 24 PDF.** La evaluación dirigida sobre la base `4792514` obtuvo 11/14 aciertos completos tras corregir moneda, ROE con notas, diagnóstico de perímetro y formulación de diferencias. Persisten dos casos de capitalización con filas fusionadas y la causa incompleta en la abstención sobre suma de activos. [Registro por caso](../quality/ROBUSTEZ_CORPUS_2026-11-19.md)

**Cierre local verificado para R08, R09 y R14.** Base publicada `9929cb2`. La muestra dirigida alcanzó 14/14 casos completos, con 8/8 cálculos exactos y 6/6 abstenciones justificadas. Se conservó la salida de los otros 11 casos. La cobertura fuera de la muestra y la publicación del cierre se registran por separado. AC-06 sigue en NOT RUN. [Detalle del cierre](../quality/ROBUSTEZ_CORPUS_2026-11-19.md)
