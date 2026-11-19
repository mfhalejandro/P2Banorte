# Auditoría funcional dirigida para la prueba real

**2026-11-19 · Codex · Trabajo posterior al simulacro.** Base 7f37024 en HEAD y origin/main, con árbol e índice Git inicialmente limpios. API y Vite activos en 8194 y 5194. Se verificó integridad y solo lectura de los originales y se reutilizó el SQLite. Se cotejaron 24 SHA de PDF con el índice y el manifiesto. Se mantuvieron las métricas del cierre de las 15:25 y la arquitectura V3. [Propuesta RCTF y plan de tres horas](PROPUESTA_RCTF_PRUEBA_REAL.md)

## Qué mostraba realmente la cita de liquidez

La página física 152 de **EEFF 2025 Grupo_.pdf** tiene el folio impreso **150**. La inspección del PNG completo y de la extracción por coordenadas confirmó que la parte superior trata pérdida potencial por riesgo de mercado, seguida por la sección **4. Riesgo de Balance y Liquidez**. Debajo de los objetivos de esa sección, una lista independiente enumera tres políticas. El encabezado de políticas está a unos 618 puntos desde arriba en una página de 792. El pie está a unos 744 puntos. La página física 153 comienza con §4.1 y añade medidas de gestión, por ejemplo planes de contingencia, que no forman parte de la respuesta auditada.

| Afirmación presentada | Respaldo en PDF p. 152 |
|---|---|
| Establecer límites globales y específicos de administración del riesgo de balance y liquidez. | Primera viñeta del encabezado de políticas. |
| Medir y monitorear el riesgo de balance y liquidez. | Segunda viñeta del mismo encabezado. |
| Informar y revelar el riesgo a áreas tomadoras de riesgos, CPR, Consejo, autoridades y público inversionista. | Tercera viñeta, con continuación alineada en la misma sección. |

Una sola cita respalda las tres afirmaciones enumeradas. La página contiene secciones consecutivas, y en este caso el texto de la lista se conservaba en el orden correcto. El corte antiguo de FTS incluía el folio porque aplanaba las líneas de la página. La respuesta lo reprodujo y omitió declarar que la selección era parcial respecto de los documentos. La cita y el visor apuntaban a la página correcta, incluso cuando inicialmente solo se veía su sección superior.

## Resultados antes y después

Se enviaron las preguntas literalmente antes de cambiar el código y se repitieron por el proxy del frontend tras la corrección. Las siglas de herramientas de la tabla representan S = search_corpus, L = list_documents, R = read_source, C = financial_calculator. Cero significa aclaración antes de invocar herramientas.

| Caso y pregunta exacta | Modo y herramientas finales | Respuesta final y evidencia | Antes → después |
|---|---|---|---|
| **D01** ¿Qué es el riesgo de crédito? | Extractivo local · 1 S y 4 R | Lo identifica como pérdida potencial por falta de pago de un acreditado o contraparte, incluidas las garantías otorgadas. El pasaje se ubica bajo el encabezado del concepto. IA Banorte ESP_16.pdf, PDF p. 29. | **PASS → PASS**. Definición específica y pertinente. |
| **D02** ¿Qué políticas de liquidez se mencionan? | Extractivo local · 1 S y 4 R | «La selección es parcial». Devuelve las tres políticas del cuadro anterior, bajo el encabezado de la Tenedora. EEFF 2025 Grupo_.pdf, PDF p. 152, folio 150. | **PARTIAL → PASS**. Antes respaldaba las tres políticas, pero incluía el folio y no acotaba el alcance. |
| **D03** ¿Qué políticas de liquidez adoptará Banorte en el año 2035? | Extractivo local · 1 S | «No encontré evidencia suficiente en los documentos indexados para responder a esta pregunta». Sin cita ni política futura inferida. | **PASS → PASS**. No hay respaldo para la afirmación solicitada. |
| **F01** Compara la capitalización de mercado en millones de dólares entre 1T24 y 2T24. Indica ambos valores, la diferencia y las fuentes. | Financiero local (doble) · 1 L, 2 S, 6 R y 1 C | **30,761** en 1T24, **22,300** en 2T24 y **−8,461 millones de dólares**. Dos citas a celdas de la fila en dólares de 2T24.pdf, PDF p. 7. | **FAIL → PASS**. Antes se abstuvo porque perdió la unidad al interpretar el indicador y no recuperó el par. |
| **F02** Compara la utilidad neta de GFNorte entre 3T24 y 3T25. ¿Cuál fue la variación y existe alguna advertencia que afecte la comparabilidad? | Financiero local (doble) · 1 L, 2 S y 7 R | Se abstiene de calcular por desconsolidación de Bineo sin base común verificada. Cita el párrafo de 3T25_vc.pdf, PDF p. 5, y muestra **14,238 millones de pesos** como dato aislado de 3T24, 4T24_1.pdf, PDF p. 5. | **PARTIAL → PASS**. Antes se abstuvo por cambio de perímetro y citó la página correcta, con un rótulo genérico en lugar del párrafo que lo demuestra. |
| **F03** Calcula la variación porcentual de la utilidad neta de GFNorte. | Financiero local (doble) · 0 | Pide indicador y dos periodos distintos. Sin cifras, citas ni búsqueda. | **PASS → PASS**. Aclara el requisito de los operandos. |

**Clasificación:** PASS acredita oráculo y citas aplicables. PARTIAL conserva contenido pertinente o una abstención segura con una deficiencia observable. FAIL significa falta del resultado exigido. NOT RUN se reserva para lo no ejecutado. Las seis consultas respondieron HTTP 200 y se comprobaron en Chromium a 390 px, con envío real a la API y apertura del visor. [Ejecutor y preguntas completas](../../tests/financial/evaluate_acceptance.py)

## Correspondencia de citas

| Métrica sobre citas emitidas | Base 7f37024 | Después |
|---|---:|---:|
| Accesibles por el endpoint PNG | 4/4 | 6/6 |
| Textuales, con afirmación o celdas localizables en el original | 3/4 | 6/6 |
| Semánticamente válidas para la afirmación que respaldan | 3/4 | 6/6 |

El primer nivel verifica HTTP, tipo PNG y firma. El segundo comprueba hash del original, página física y presencia de los pasajes o celdas de la referencia. El tercero exige contexto además del texto. D01 conserva encabezado y definición. D02 ubica las viñetas bajo el título correcto, entre la sección de riesgo de mercado y el pie. F01 coteja centros de fila y columna, encabezados trimestrales, moneda y escala, y recalcula la diferencia con Decimal. F02 localiza el párrafo que nombra a Bineo y limita la comparabilidad, y vincula la cifra aislada a la columna base. Las abstenciones sin citas quedan fuera del denominador. La validez de las tres afirmaciones D02 coexistía con un defecto de la respuesta, por lo que esa fila conserva PARTIAL en la base.

## Correcciones y regresiones

- **D02, extracción y alcance.** Se leen viñetas del original asociadas a un encabezado que contiene el tema solicitado. Los límites de posición acotan continuaciones y excluyen folios y columnas ajenas. Se permiten hasta dos evidencias distintas de un máximo de cuatro lecturas. Cuando faltan elementos verificables, el flujo se abstiene. La respuesta explica que la selección es parcial. Un test con dos fuentes y una columna distractora verifica cobertura y abstención. [Agente](/var/www/P2Banorte/apps/api/agent.py) · [Corpus](/var/www/P2Banorte/apps/api/corpus.py)
- **F01, interpretación de unidad.** El planificador separa moneda y escala del nombre de la métrica antes de buscar, tanto antes como después del intervalo. Una unidad contradictoria abstiene antes de invocar herramientas. El parser existente conserva su asociación de periodos y celdas. [Agente financiero](/var/www/P2Banorte/apps/api/financial_agent.py)
- **F02, evidencia de comparabilidad.** La lectura conserva el párrafo original de la advertencia de perímetro, prioriza el contexto explícito de no comparabilidad y nombra la desconsolidación de Bineo cuando la fuente la acredita. Se conserva la abstención segura si solo hay una señal sin un fragmento verificable. [Lectura financiera](/var/www/P2Banorte/apps/api/financial_evidence.py)

| Control local | Resultado |
|---|---|
| Regresión P0, SPEC-002 y arnés | **PASS** · 48 pruebas Python y 5 subcasos. Aviso preexistente de Starlette. |
| Robustez financiera de 14 casos, reejecutada | **PASS** · 14/14, 8 cálculos, 6 abstenciones y 25/25 PNG. Trece respuestas y sus citas coincidieron con el cierre. R11 conserva la abstención, los valores comprobados y las páginas. El texto de la advertencia ahora cita el párrafo sobre Bineo. |
| Smoke de navegador aislado | **PASS** · 6 casos. |
| Aceptación con el corpus de ensayo | **PASS** · 6/6 con cotejo semántico y 6/6 citas abiertas en Chromium. |
| SPEC-002-AC-06, proveedor generativo real | **NOT RUN** · autorización independiente pendiente. |
| Evaluación contra otros layouts y entorno final | **PARTIAL** · pendiente de corpus, runtime y oráculos reales. |
| GitHub Actions para estos cambios | **NOT RUN** · cambios locales para revisión. |

La extracción de listas depende de encabezados, viñetas y geometría reconocibles. PDFs sin texto seleccionable o agrupaciones ambiguas pueden producir abstención. La validación semántica es una suite dirigida con oráculos del ensayo, no un verificador universal. El modo financiero local usa un doble determinista. El visor genera PNG sin interpretación multimodal.

## Reproducción

Arranca ambos servicios con el índice existente según el [README](../../README.md). Desde la raíz, con el frontend en 5194:

~~~bash
.venv/bin/python -B tests/financial/evaluate_acceptance.py --data docs/requirements/data > /tmp/p2-aceptacion.jsonl
.venv/bin/python -B -m pytest -p no:cacheprovider -q tests/p0 tests/financial tests/harness
npm --prefix apps/web run smoke
~~~

El ejecutor escribe pregunta, respuesta, modo, herramientas, localización, accesibilidad, texto, respaldo semántico y veredicto en JSONL. El código de salida es distinto de cero si un caso no pasa. Se puede usar una captura previa con --recorded. Para reproducir la línea base, inicia 7f37024 en otro puerto de loopback, con el mismo par RAG_DATA_DIR y RAG_STATE_DIR, y pasa su origen HTTP con --base. La salida y los PDF derivados deben guardarse fuera del repositorio. Para cotejo manual, pega las seis preguntas en el navegador y abre las citas. En D02 desplázate a la parte inferior de la página, hasta la lista posterior a los objetivos. Para los casos financieros usa los encabezados y notas de la página. [Reproducción de los 14 casos históricos](ROBUSTEZ_CORPUS_2026-11-19.md#reproducción)

## Seguimiento de robustez lingüística sobre 68d2783

La consulta «¿Cuáles son las políticas de riesgo de liquidez de la Tenedora? Enumera las políticas identificadas y señala en qué documento y página se encuentra cada una.» devolvía abstención. La versión corta seguía respondiendo. Antes del ajuste, EXPLANATION_PROMPT no reconocía la forma «cuáles son». FTS exigía 8 de 10 términos y contaba instrucciones como «enumera», «señala», «página» y «cada». No llegó a leer la página original.

El flujo documental elimina cláusulas completas de presentación reconocidas y usa la misma consulta normalizada para recuperar y seleccionar pasajes. En esta pregunta se conserva el tema con su entidad, «políticas», «riesgo», «liquidez» y «Tenedora». Se mantiene el umbral del 80 %, la exigencia de coincidencias numéricas aplicables y la validación del encabezado original. Los negativos conservan el año, la unidad o la referencia explícita. Cuando una consulta incluye restricciones que el extractivo no puede acreditar, comunica falta de evidencia. Una segunda lectura con las mismas viñetas se deduplica aun si solo cambia el artículo inicial.

Los cuatro cambios de formulación de D02 conservan las tres políticas y su cita a EEFF 2025 Grupo_.pdf, página física 152. D03a mantiene la abstención para 2035. Los seis casos originales y las cinco variantes pasaron el cotejo automatizado y Chromium, con 10/10 citas accesibles, 10/10 textuales y 10/10 semánticas. Se reprodujeron los 14 casos financieros con las mismas respuestas, citas y herramientas de la última auditoría. El modo generativo real continúa NOT RUN.

Para reproducir también las variantes, usa el ejecutor de aceptación con la opción --paraphrases:

~~~bash
.venv/bin/python -B tests/financial/evaluate_acceptance.py --data docs/requirements/data --paraphrases > /tmp/p2-aceptacion-parafrasis.jsonl
~~~
