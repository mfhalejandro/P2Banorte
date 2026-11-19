---
id: SPEC-002
title: Comparación financiera trazable con herramientas V3
version: 1
status: IMPLEMENTED
owner: Solicitante humano
reviewers: [Solicitante humano]
created_at: '2026-11-19'
updated_at: '2026-11-19'
prd_requirements: [AC-02, AC-03, AC-07, AC-08, AC-09, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-18, AC-19, AC-21, AC-25, AC-26, AC-27]
adrs: []
sdds: [SDD-002]
dependencies: [SPEC-001]
implementation_plan: plans/implementation-spec-002-financiero.md
sprint_tasks: [F-01, F-02, F-03, F-04]
quality_gates: [SPEC_QUALITY_GATE]
supersedes: null
superseded_by: null
approval:
  by: Solicitante humano
  date: '2026-11-19'
  evidence: "Conversación del proyecto. Aprobación funcional expresa de SPEC-002 v1 para implementación local. AC-06 diferido."
---

# SPEC-002 · Comparación financiera trazable con herramientas V3

**Versión 1 · Aprobada para implementación local.** Ante una pregunta por la variación de un mismo indicador entre dos periodos, el analista obtiene ambos valores con sus periodos y unidades, un resultado calculado por el backend y una cita a la página original por operando. Si la comparación carece de respaldo, recibe una explicación específica. El primer corte demuestra una comparación válida y una abstención. [PRD V3](../docs/requirements/PRD.md) · [Contexto financiero](../docs/requirements/context_for_the_professional.md) · [Stack](../docs/requirements/technology_stack.md) · [P0](SPEC-001-cita-pdf.md)

## Recorrido y límites

1. El agente busca cada periodo por separado en el catálogo dinámico. Conserva un solo agente, FastAPI, PyMuPDF, SQLite FTS5/BM25, React y el contrato vigente de chat, citas y visor. Las herramientas tipadas son `list_documents`, `search_corpus`, `read_source`, `financial_calculator` e `inspect_page_visual`. El catálogo admite paginación, el render visual se realiza localmente y las llamadas comparten un límite de pasos y tiempo.
2. La preparación local usa PDF ficticios y un doble determinista que propone llamadas y recibe resultados. Los argumentos se validan antes de ejecutar y únicamente se admiten herramientas y referencias habilitadas. El estado del proveedor y los errores recuperables son visibles. El P0 sigue siendo un modo extractivo independiente y conserva su índice. El PDF se trata como contenido documental y la respuesta pública omite credenciales y razonamiento interno.
3. La verificación de inferencia generativa real es una evidencia separada, pendiente de autorización de proveedor, endpoint, modelo y alcance de datos y costo. Con esa autorización, la primera prueba usa datos sintéticos y verifica desde el backend un ciclo completo de llamada, resultado y respuesta final. El uso del agente codificador no aporta credenciales para ese ciclo.
4. Se evalúa primero con 1–2 PDF y después con un lote diverso, ampliando al corpus legible según recursos y evidencia de calidad. El índice de ensayo se mantiene separado. La ingesta descubre nombres, tipos y periodos en ejecución, registra alias por SHA y aísla documentos fallidos. Un fallo de ingesta deja disponible el índice anterior. La evaluación usa oráculos cotejados, cobertura por periodo, acierto de citas, exactitud numérica con unidad, abstención, latencia y RSS dentro del presupuesto de 2 CPU/4 GB. El ensayo local y Coder se reportan por separado. Las ampliaciones opcionales y el despliegue siguen fuera de este corte.

## Procedencia y lectura de tablas

- Cada operando parte de un `source_id` emitido por una lectura de esta solicitud. Se conserva documento, página desde 1, valor tal como figura en la fuente, métrica, entidad, periodo, tipo de periodo, unidad, escala, moneda y base contable pertinente. Una referencia inventada, caducada o ajena a la solicitud invalida el operando.
- Si el dato viene en texto, el pasaje debe asociar inequívocamente el valor con el indicador y su contexto. El valor completo se contrasta con la fuente, considerando signo y separadores únicamente si la convención es inequívoca. El estado `grounded` acredita que el número completo aparece en la fuente, `not_found` indica que falta y `not_applicable` se reserva para evidencia sin afirmación numérica. Para calcular hace falta además verificar que la cifra pertenece al indicador y al periodo correctos.
- Si el dato viene en tabla, `read_source` extrae bajo demanda 1–3 páginas consultadas. El respaldo comprende la celda, sus encabezados de fila y columna con los niveles necesarios, unidad, escala y notas que cambien la interpretación. Se conserva la ruta hacia la página original. Si hay encabezados desplazados, varias celdas plausibles, notas que no se pueden asociar o unidad indeterminada, se marca evidencia ambigua y se omite el cálculo. El usuario puede inspeccionar la página para aclararlo.

## Comparabilidad y cálculo

- **Métrica, entidad y perímetro.** Ambos valores deben medir el mismo indicador, de la misma entidad, con definición, perímetro y base contable comparables. Una reexpresión exige evidencia explícita de la base común y una advertencia con cita. Un cambio de perímetro, como una desconsolidación, impide calcular cuando no hay una serie comparable respaldada.
- **Periodo.** Verificar el periodo solicitado en cada fuente y su tipo y duración. Dos trimestres se pueden comparar si las demás condiciones se cumplen. Un trimestre frente a un acumulado de nueve meses, o acumulados de distintas duraciones, requieren abstención.
- **Unidad, escala y moneda.** Exigir unidades compatibles y la misma moneda cuando aplique. Solo se admite normalización exacta de escala explícita, por ejemplo miles a millones de MXN, mostrando la unidad resultante y conservando los valores de origen. El corte excluye conversiones cambiarias implícitas.
- **Decimal.** El backend recibe representaciones decimales como texto, valida valores finitos y límites de entrada y evita `float`. Si B es el periodo base y A el consultado, diferencia = A − B y variación relativa = (A − B) ÷ B × 100. La variación relativa requiere B > 0 en este corte. La razón A ÷ B exige par comparable y denominador distinto de cero. La suma A + B requiere una magnitud aditiva y periodos sin solapamiento. Un saldo de cierre o una tasa carecen de esa aditividad temporal. Restar dos tasas da puntos porcentuales. El cálculo conserva la precisión de los operandos y aplica redondeo únicamente para la presentación cuando hay más de dos decimales, con empate al par. La respuesta toma fórmula, resultado y unidad de la calculadora del backend.
- **Abstención.** Si falta un periodo o un valor, falla la procedencia, los datos resultan incompatibles o la operación no está definida, se comunica el motivo y se omite el resultado numérico de la operación. Se pueden mostrar por separado las cifras verificadas con su contexto y citas. Una caída del proveedor se indica como error operativo recuperable.

## Aceptación y trazabilidad

| Criterio | Resultado observable | Prueba prevista |
|---|---|---|
| SPEC-002-AC-01 | El doble local completa un ciclo tipado de herramientas. Límite agotado, plazo vencido o fallo del proveedor producen un resultado controlado, con el modo visible. | T-10/T-11 |
| SPEC-002-AC-02 | Se recupera evidencia por periodo y se usan encabezado y celda correctos, incluso si el mismo número aparece en otra celda. Cada cita abre la página que sustenta su operando. | T-05/T-06 y apertura dirigida |
| SPEC-002-AC-03 | En el caso ficticio de utilidad neta de Grupo Faro, de 111.11 a 123.40 millones de MXN, la diferencia es 12.29 millones y la variación presentada es 11.06 %. De 11.0 % a 12.5 % la diferencia es 1.5 puntos porcentuales. El caso trimestre frente a acumulado y los casos de entidad, moneda o perímetro distintos, celda ambigua, referencia inventada, cifra ausente y denominador inválido se abstienen con motivo. Se prueba también el rechazo de números no finitos y la validez de una razón y de una suma aditiva. | T-07/T-08 y criterios AC-11 a AC-15 del PRD |
| SPEC-002-AC-04 | Dos conjuntos con nombres y hashes distintos se descubren en ejecución. Un duplicado genera un alias, la reingesta reutiliza contenido y un PDF fallido queda aislado. El informe contiene oráculos, fallos y mediciones. | T-02/T-13/T-14/T-16 |
| SPEC-002-AC-05 | El P0 conserva su modo extractivo y se vuelve a verificar la apertura de una cita si cambia su código o interfaz compartida. | Regresión dirigida T-09 |
| SPEC-002-AC-06 | El proveedor real completa un ciclo sintético desde el backend, con autorización independiente y resultado registrado por separado. | T-10 en entorno autorizado |

## Gobierno

2026-11-19 · Codex presenta SPEC-002 v1 desde `4620231`. El solicitante autorizó la preparación local y pruebas sintéticas con doble. El solicitante aprobó la implementación local de AC-01 a AC-05. AC-06 sigue pendiente de autorización independiente y no condiciona las pruebas locales. El ADR de proveedor se abrirá cuando haya una elección autorizada. Tras aprobar la spec se registra el plan ejecutable y el diseño detallado aplicable del intercambio de herramientas. La comprobación preparatoria de fixtures y la línea base P0 se registran por separado de los criterios SPEC-002, documentados en la bitácora. [Trazabilidad](../docs/quality/TRACEABILITY_MATRIX.md)

2026-11-19 · IN_REVIEW → APPROVED. Aprobación expresa para el corte local. [Plan](../plans/implementation-spec-002-financiero.md) · [SDD local](../docs/architecture/sdd/SDD-002-comparacion-local.md).

2026-11-19 · APPROVED → IN_PROGRESS → IMPLEMENTED (tramo local). AC-01 a AC-05 pasaron los controles locales. AC-06 permanece NOT RUN, pendiente de autorización independiente.
