# Trazabilidad de la entrega

| Fuente | Tarea verificable | Prueba / evidencia | Estado |
|---|---|---|---|
| Estándar §§3.11, 4, PRD AC-22 | Identificar la línea base y proteger las fuentes durante el desarrollo | Verificador RCTF, IntegrityTests, bitácora | PASS, hashes y estado independiente verificados en P0 |
| Estándar §14, PRD AC-23, T-15 | Detectar contenido no publicable en las superficies de Git | PublicationTests, gate sobre el índice real | Hallazgo inicial del ZIP resuelto en el índice de 816e4ba; revisión de publicación aplicable |
| Formato §3, estándar §§8–12 | Entrada portable y elección de skill | Diez frontmatters y recorridos de la bitácora | Validación local |
| PRD AC-16, T-09 · [SPEC-001-AC-01](../../specs/SPEC-001-cita-pdf.md) | Abrir la página correcta desde una respuesta | P0, prueba UI/API sobre un documento indexado | PASS, imagen cotejada y prueba de navegador |
| PRD AC-17, T-09 · SPEC-001-AC-02 | Rechazar referencia inválida sin exponer rutas | Prueba API/UI prevista | PASS en el sprint P0 |
| PRD AC-18 · SPEC-001-AC-03 | Comunicar ausencia de respaldo | Evaluación de consulta fuera del corpus | PASS en el sprint P0 |
| PRD AC-01/03/10 · SPEC-001-AC-04 | PDF a índice idempotente con originales íntegros | P0-01, T-01/T-02 | PASS en el sprint P0 |
| PRD AC-04/05/06 · SPEC-001-AC-05 | Recuperar por consulta financiera y ranking BM25 | P0-02, T-03/T-04 | PASS en el sprint P0 |
| PRD AC-19 · SPEC-001-AC-06 | Del agente y sus herramientas a la respuesta, con fallo controlado | P0-02 a P0-04, T-09/T-10 | PASS en el sprint P0 |
| PRD AC-11 a AC-15, T-07/T-08 | Cálculo con operandos comparables y procedencia | Pruebas de contrato y abstención de la etapa de aplicación | NOT RUN |
| PRD AC-25/AC-26, T-16 | Descubrir corpus variable y deduplicar por contenido | Ingesta con dos conjuntos de prueba | NOT RUN |

Al aprobar una spec, añadir su identificador y plan a las filas correspondientes. Conservar referencia a la ejecución real y al cambio verificado.

## Corte financiero local · SPEC-002 v1

| Requisito | Criterio | Prueba y evidencia | Estado |
|---|---|---|---|
| PRD AC-19 y AC-21 | SPEC-002-AC-01 | T-10/T-11, doble local inyectado, herramienta inválida, límite, caída y espera | PASS local |
| PRD AC-07/09/16/18 | SPEC-002-AC-02 | T-05/T-06, celda y encabezado comprobados, visor en Chromium y cotejo de página real | PASS local |
| PRD AC-11 a AC-15 | SPEC-002-AC-03 | T-07/T-08, Decimal, dos citas, diferencias de moneda, perímetro y duración | PASS local |
| PRD AC-02/03/08/10/25–27 | SPEC-002-AC-04 | T-02/T-13/T-14/T-16, dos corpus ficticios, recuperación ante interrupción y ensayo progresivo sobre 24 PDF | PASS local |
| PRD AC-16/18/19 | SPEC-002-AC-05 | T-09, consulta y PNG sobre estado previo de P0 sin migración | PASS local |
| PRD AC-19 y AC-21 | SPEC-002-AC-06 | T-10, ciclo sintético con proveedor real | NOT RUN, autorización independiente pendiente |

La [evaluación dirigida de robustez](ROBUSTEZ_CORPUS_2026-11-19.md) amplía la evidencia de SPEC-002 en AC-01 a AC-05. Registra por separado exactitud, abstenciones y cobertura de tablas pendientes. AC-06 sigue en NOT RUN.

| Cierre | Criterio | Evidencia | Resultado |
|---|---|---|---|
| R08/R09, capitalización por moneda y periodo | SPEC-002-AC-02/03 · T-05/T-06/T-07/T-08 | Pruebas con filas y columnas reordenadas, tabla ambigua y verificación real de `2T24.pdf`, p. 7 | VERIFIED en muestra local |
| R14, saldo no aditivo | SPEC-002-AC-03 · T-07 | Rechazo previo a recuperación, con catálogo indisponible en fixture | VERIFIED |
| Regresión P0 y SPEC-002 local | SPEC-001-AC-01/02/06 y SPEC-002-AC-01 a AC-05 · T-09/T-12/T-13 | Mismas 14 consultas y 25 PNG; Python y navegador P0 | VERIFIED en muestra local |
| Proveedor generativo real | SPEC-002-AC-06 | Autorización independiente pendiente | NOT RUN |

[Resultados finales y reproducción](ROBUSTEZ_CORPUS_2026-11-19.md#cierre-del-simulacro-sobre-la-base-publicada-9929cb2)
