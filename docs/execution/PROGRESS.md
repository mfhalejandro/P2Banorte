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

**Auditoría previa a la prueba real, VERIFIED en la muestra local.** Se corrigieron la contaminación por folio en listas, la unidad financiera antepuesta a los periodos y el extracto de la advertencia de Bineo. Pasan los seis nuevos casos y los 14 de robustez reejecutados. La generalización a la entrega de Coder sigue PARTIAL. La propuesta RCTF queda pendiente de revisión humana. [Auditoría](../quality/AUDITORIA_FUNCIONAL_PRUEBA_REAL.md) · [Propuesta y reloj operativo](../quality/PROPUESTA_RCTF_PRUEBA_REAL.md)

**Robustez lingüística, VERIFIED en la muestra local.** Las cinco variantes de D02 y D03 pasaron junto con los seis casos originales. Se conservan las políticas y su cita al cambiar el orden de instrucciones, y la variante con 2035 sigue absteniéndose. [Evidencia y reproducción](../quality/AUDITORIA_FUNCIONAL_PRUEBA_REAL.md#seguimiento-de-robustez-lingüística-sobre-68d2783)

**Intención operativa P01–P08, VERIFIED en la muestra.** Las ocho preguntas exactas pasaron en Chromium. Se conservaron las abstenciones por futuro, periodos incompatibles y saldo no aditivo. [Resultados y reproducción](../quality/AUDITORIA_FUNCIONAL_PRUEBA_REAL.md#generalización-lingüística-p01p08-sobre-d747950)

**DeepSeek real sintético, VERIFIED.** FastAPI completó el ciclo de herramientas con deepseek-flash sin thinking y pasó 10/10 en la batería final. La demo de 24 PDF conserva financial-local. [Evidencia y límites](../quality/AUDITORIA_FUNCIONAL_PRUEBA_REAL.md#deepseek-real-sobre-un-corpus-sintético--a-partir-de-2fab9ef)

**Evaluación A/B G01–G22, VERIFIED en la pasada autorizada.** Financial-local reprodujo 16/22 y DeepSeek obtuvo 7/22, con tres fallos operativos. Generalización PARTIAL. La comparación favorece mantener financial-local para la prueba real. Las dos instancias temporales se detuvieron. DeepSeek fuera de la muestra autorizada queda NOT RUN. [Comparación y límites](../quality/AUDITORIA_FUNCIONAL_PRUEBA_REAL.md#evaluación-ab-g01g22)
