# Estado del proyecto

**Simulacro cerrado sobre `5307d2b`.** El PRD aprobado y la arquitectura V3 congelada enmarcan [SPEC-001 v2](../../specs/SPEC-001-cita-pdf.md) y [SPEC-002 v1](../../specs/SPEC-002-comparacion-financiera.md). En GitHub, `Spec quality` aprobó la estructura y trazabilidad de la entrega publicada. [Ejecución de GitHub Actions](https://github.com/mfhalejandro/P2Banorte/actions/runs/44613640612)

| Estado | Alcance |
|---|---|
| **VERIFIED** | P0 extractivo, recuperación de evidencia, citas y visor PNG, y comparación financiera local con Decimal. La muestra dirigida obtuvo 14/14 aciertos completos, 8/8 cálculos exactos y respaldados, 6/6 abstenciones justificadas y 25/25 PNG válidos. Pasaron 41 pruebas Python, 5 subcasos y 6 pruebas de navegador. |
| **PARTIAL** | Generalización a otros layouts y formatos financieros y evaluación fuera de la muestra o en el entorno final. Las tablas ambiguas o sin moneda comparable pueden producir abstención. |
| **NOT RUN** | AC-06 de SPEC-002. La integración con un proveedor generativo real requiere autorización independiente. `financial-local` usa un doble determinista. |

Los 5/14 y 11/14 son mediciones históricas. El 14/14 corresponde al cierre publicado en `5307d2b` y a su confirmación local con los mismos 14 casos. [Informe y recuperación del estado](../quality/ROBUSTEZ_CORPUS_2026-11-19.md) · [Bitácora](EXECUTION_LOG.md)

Las instrucciones de instalación y ejecución se mantienen en el [README](../../README.md). El [sprint](SPRINTS.md) registra qué se verificó para el cierre.

**Mantenimiento posterior al cierre, VERIFIED localmente.** La demo de 24 PDF recuperó API y web en unidades independientes. P0 y SPEC-002 comparten el índice y se seleccionan por consulta en el modo financiero local. [Verificación posterior al cierre](EXECUTION_LOG.md)
