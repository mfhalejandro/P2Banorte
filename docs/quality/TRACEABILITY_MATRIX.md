# Trazabilidad de la entrega

| Fuente | Tarea verificable | Prueba / evidencia | Estado |
|---|---|---|---|
| Estándar §§3.11, 4, PRD AC-22 | Identificar la línea base y proteger las fuentes durante el desarrollo | Verificador RCTF, IntegrityTests, bitácora | PASS en el cierre de 5307d2b, 24 SHA cotejados con el manifiesto y el índice |
| Estándar §14, PRD AC-23, T-15 | Detectar contenido no publicable en las superficies de Git | PublicationTests, gate sobre el índice real | PASS sobre la entrega publicada y el índice documental de cierre |
| Formato §3, estándar §§8–12 | Entrada portable y elección de skill | Diez frontmatters y recorridos de la bitácora | Validación local |
| PRD AC-16, T-09 · [SPEC-001-AC-01](../../specs/SPEC-001-cita-pdf.md) | Abrir la página correcta desde una respuesta | P0, prueba UI/API sobre un documento indexado | PASS, imagen cotejada y prueba de navegador |
| PRD AC-17, T-09 · SPEC-001-AC-02 | Rechazar referencia inválida sin exponer rutas | Prueba API/UI ejecutada | PASS en el sprint P0 |
| PRD AC-18 · SPEC-001-AC-03 | Comunicar ausencia de respaldo | Evaluación de consulta fuera del corpus | PASS en el sprint P0 |
| PRD AC-01/03/10 · SPEC-001-AC-04 | PDF a índice idempotente con originales íntegros | P0-01, T-01/T-02 | PASS en el sprint P0 |
| PRD AC-04/05/06 · SPEC-001-AC-05 | Recuperar por consulta financiera y ranking BM25 | P0-02, T-03/T-04 | PASS en el sprint P0 |
| PRD AC-19 · SPEC-001-AC-06 | Del agente y sus herramientas a la respuesta, con fallo controlado | P0-02 a P0-04, T-09/T-10 | PASS en el sprint P0 |
| PRD AC-11 a AC-15, T-07/T-08 | Cálculo con operandos comparables y procedencia | T-07/T-08, contrato Decimal, procedencia y abstención en SPEC-002 | VERIFIED en la muestra y las regresiones locales |
| PRD AC-25/AC-26, T-16 | Descubrir corpus variable y deduplicar por contenido | T-16, dos corpus ficticios distintos y deduplicación por SHA | VERIFIED en pruebas locales |

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

La [evaluación dirigida de robustez](ROBUSTEZ_CORPUS_2026-11-19.md) amplía la evidencia de SPEC-002 en AC-01 a AC-05. Conserva 5/14 y 11/14 como mediciones históricas y 14/14 como cierre publicado en `5307d2b`. SPEC-002-AC-06 permanece en NOT RUN.

| Cierre | Criterio | Evidencia | Resultado |
|---|---|---|---|
| R08/R09, capitalización por moneda y periodo | SPEC-002-AC-02/03 · T-05/T-06/T-07/T-08 | Pruebas con filas y columnas reordenadas, tabla ambigua y verificación real de `2T24.pdf`, p. 7 | VERIFIED en muestra local |
| R14, saldo no aditivo | SPEC-002-AC-03 · T-07 | Rechazo previo a recuperación, con catálogo indisponible en fixture | VERIFIED |
| Regresión P0 y SPEC-002 local | SPEC-001-AC-01/02/06 y SPEC-002-AC-01 a AC-05 · T-09/T-12/T-13 | 14/14 casos completos, 8/8 cálculos, 6/6 abstenciones justificadas y 25/25 PNG. 41 pruebas Python, 5 subcasos y 6 pruebas de navegador | VERIFIED en muestra local |
| Cobertura y entorno final | SPEC-002-AC-02/04 | Generalización a otros formatos y evaluación fuera de la muestra o en el entorno final pendientes de evidencia | PARTIAL |
| Proveedor generativo real | SPEC-002-AC-06 | Autorización independiente pendiente | NOT RUN |

[Resultados finales y reproducción](ROBUSTEZ_CORPUS_2026-11-19.md#cierre-publicado-en-5307d2b)

## Corrección posterior al cierre

| Criterio | Evidencia | Resultado |
|---|---|---|
| SPEC-001-AC-01/03/06, SPEC-002-AC-01/03/05 | Regresiones de enrutamiento, definiciones con columna, aclaración y comparabilidad. Chromium con 24 PDF y seis citas abiertas. Cotejo de los 14 casos financieros con el cierre. | VERIFIED localmente. [Bitácora](../execution/EXECUTION_LOG.md) |

## Auditoría previa a la prueba real

| Criterio vigente | Evidencia posterior al simulacro | Resultado |
|---|---|---|
| SPEC-001-AC-01/03/06, PRD RF-10 y T-09/T-13 | D01–D03 con definiciones, listas bajo encabezado y ausencia de evidencia futura. Cotejo de elementos y del folio impreso en la página física. | VERIFIED localmente. |
| SPEC-002-AC-02/03/05 y T-05/T-06/T-07/T-08 | F01–F03 con cruce fila/columna y moneda, advertencia original de Bineo y aclaración. Reejecutados los 14 casos de robustez. | VERIFIED localmente. |
| SPEC-002-AC-06 | Comprobación sintética desde FastAPI propuesta para el preflight real. | NOT RUN. |

[Informe y reproducción](AUDITORIA_FUNCIONAL_PRUEBA_REAL.md) · [Propuesta RCTF](PROPUESTA_RCTF_PRUEBA_REAL.md)

| Seguimiento | Evidencia | Resultado |
|---|---|---|
| PRD RF-03/RF-10 y SPEC-001-AC-01/03/06 | D02a–D02d y D03a comprueban paráfrasis, orden de instrucciones, contexto de la Tenedora, fuente y año. | VERIFIED localmente. |

| Generalización | Evidencia | Resultado |
|---|---|---|
| PRD RF-03, RF-07 a RF-10 y T-05/T-07/T-13 | P01–P08, paráfrasis, restricciones negativas y validación semántica del original. | VERIFIED en la muestra local. [Auditoría](AUDITORIA_FUNCIONAL_PRUEBA_REAL.md) |

### Auditoría B01–B10 posterior al simulacro

| Criterio | Verificación | Estado |
|---|---|---|
| SPEC-001-AC-01/03/05, RF-03 y RF-10 | B01–B03 y B10. Definición, continuación de sección, alcance y abstención futura, con contraste sobre la página original. | VERIFIED en la muestra de desarrollo. |
| SPEC-002-AC-01 a AC-05 y T-05/T-07/T-08/T-09 | B04–B09. Dos monedas con operando individual, comparación entre tasas, participación, restricción de periodos, cambio de perímetro y stock. Regresiones 14/14, 11/11 y 28/28. | VERIFIED en la muestra local. |
| T-13 · Generalización | G01–G22 con oráculos y código congelados. 16 PASS, 1 PARTIAL y 5 FAIL. | PARTIAL. |
| SPEC-002-AC-06 | Proveedor real y entorno de evaluación. | NOT RUN. |

[Resultados, causas, métricas y comandos](AUDITORIA_FUNCIONAL_PRUEBA_REAL.md#b01b10-y-generalización-independiente-sobre-a156744)

### DeepSeek real con datos ficticios

| Criterio | Evidencia posterior al simulacro | Estado |
|---|---|---|
| SPEC-002-AC-06 | FastAPI y deepseek-flash sin thinking. Intercambio real de herramientas, argumentos validados, dos operaciones respaldadas y 12 citas cotejadas en la ejecución final. | VERIFIED en corpus sintético. |
| SPEC-001-AC-01/03/06 y SPEC-002-AC-01 a AC-05 | Se conservaron P0, Decimal, comparabilidad y visor. Instrucción en PDF sin ejecución, transportes inválidos y recuperación tras timeout. | VERIFIED en pruebas locales. |
| Frontera de inferencia y corpus real | Chat bloqueado con la política desactivada, cero llamadas en la prueba simulada, modo sintético separado. Evaluadores G01–G22 y H01–H08 preparados. | Política VERIFIED. Evaluación real NOT RUN. |

[Resultados y métricas](AUDITORIA_FUNCIONAL_PRUEBA_REAL.md#deepseek-real-sobre-un-corpus-sintético--a-partir-de-2fab9ef)

### Comparación A/B G01–G22 posterior al simulacro

| Criterio | Evidencia | Estado |
|---|---|---|
| T-13 · Generalización independiente | Misma versión, oráculos y corpus. Local 16/22 y DeepSeek 7/22, con tres HTTP 503 separados del fallo de calidad. | PARTIAL, recomendación de mantener financial-local. |
| SPEC-002-AC-06 · Proveedor real | Tool calling desde FastAPI con DeepSeek Flash. Una pasada G01–G22 autorizada, comparación de citas, 98 llamadas y ledger conciliado. | VERIFIED en el alcance autorizado. Fuera de esa muestra está NOT RUN. |

[Resultados, controles y limitaciones](AUDITORIA_FUNCIONAL_PRUEBA_REAL.md#evaluación-ab-g01g22)

### Rescate híbrido experimental

| Criterio | Evidencia | Estado |
|---|---|---|
| SPEC-002-AC-01/02/03/05 y T-05/T-07/T-11 | Plan tipado sin herramientas remotas, comparabilidad y cálculos locales. Fallback ante timeout, plan inválido y presupuesto agotado. Regresiones 14/14, 11/11, 28/28, B01–B10 y Chromium. | VERIFIED en pruebas locales. |
| SPEC-002-AC-06 · Ámbito híbrido | Pasada única autorizada G01–G22 con cuatro planes. Los 16 PASS de control conservaron evidencia y texto sin llamadas. Ledger original conciliado. | VERIFIED para la pasada autorizada. |
| T-13 · Validación fuera de desarrollo | 21/22 en G01–G22 y 5/20 en cada variante local de J01–J20. El control sin términos propuestos fue mejor en G01. J16 conserva un fallo de moneda de la línea base. | PARTIAL. Mantener financial-local. |

[Protocolo, evidencia e incidente inicial de P0](AUDITORIA_FUNCIONAL_PRUEBA_REAL.md#búsqueda-híbrida-experimental)

### Sprint de generalización híbrida

| Criterio | Evidencia | Resultado |
|---|---|---|
| SPEC-002-AC-01/02/03, T-05/T-07/T-11 | Cobertura por apartado, evidencia original, rechazo de divisas sin respaldo y preservación ante fallos del plan. 97 pruebas Python, 5 subcasos y regresiones de producto. | VERIFIED localmente. |
| T-13 · Generalización | K01–K12 congelada. 7/12 local y 9/12 híbrido simulado. Los siete PASS se preservaron y se acreditaron dos rescates nuevos. | PARTIAL, evidencia exploratoria sin atribución a DeepSeek. |
| SPEC-002-AC-06 · Ablación externa K | Preparado con límite de gasto y lista exacta. Requiere autorización del alcance para esta pasada. | NOT RUN en este sprint. |

[Auditoría, recursos y oráculos](AUDITORIA_FUNCIONAL_PRUEBA_REAL.md#sprint-de-generalización-híbrida)

### Rescate determinista en la demo web

| Criterio | Evidencia | Resultado |
|---|---|---|
| SPEC-001-AC-01/03/06 y SPEC-002-AC-01/02/03/05 | Producción con Plan y Step, verificación de apartados, dos comparaciones compuestas y apertura de PNG desde Vite. | VERIFIED en la batería de 20 preguntas, 20/20 y 31/31 citas pertinentes. |
| T-10/T-11 · Frontera externa y fallback | Transporte y configuración remotos inalcanzables con alcance bloqueado. Pruebas de timeout, esquema inválido y abstenciones de moneda, calendario y perímetro. | VERIFIED, cero consumo externo. |
| T-13 · Regresión conocida | Las variantes local e híbrida usaron el mismo corpus, índice y versión. B preservó 13/13 PASS de A en la batería visual. G, J y K también se reejecutaron. | VERIFIED en las baterías citadas. |

[Comparación por ID, citas y latencias](AUDITORIA_FUNCIONAL_PRUEBA_REAL.md#rescate-determinista-local-en-la-aplicación-web)

### Generalización del híbrido determinista

| Criterio | Evidencia | Resultado |
|---|---|---|
| SPEC-001 y SPEC-002-AC-01/02/03/05 | L pasa de 6/25 a 25/25 con 42/42 citas cotejadas. La demo de 24 PDF abre los PNG de L02 y L15 desde Chromium. | VERIFIED en L. |
| T-05/T-07/T-11 | R01–R14, pruebas de periodos, sumas de stock, divisas y perímetro. Bloqueo de salida, once negativos M/L y verificación original de celdas. | VERIFIED para los cálculos emitidos y los rechazos acreditados. Cobertura abierta PARTIAL. |
| T-13 | Visual 20/20, G 22/22, J 15/20 y K 11/12 sin pérdidas de veredictos frente al registro anterior. Una pasada congelada de M obtuvo 5 PASS, 3 PARTIAL y 4 FAIL. | Regresiones VERIFIED. Generalización PARTIAL. |
| SPEC-002-AC-06 | Pruebas locales con alcance externo bloqueado. Cero llamadas, tokens y costo. | NOT RUN en este trabajo. |

[Diagnóstico, comparaciones y límites](AUDITORIA_FUNCIONAL_PRUEBA_REAL.md#generalización-del-híbrido-determinista--línea-base-2fa82a6)
