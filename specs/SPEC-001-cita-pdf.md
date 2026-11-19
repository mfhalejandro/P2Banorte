---
id: SPEC-001
title: Consulta financiera P0 con evidencia y página original
version: 2
status: IMPLEMENTED
owner: Solicitante humano
reviewers: [Solicitante humano]
created_at: '2026-11-19'
updated_at: '2026-11-19'
prd_requirements: [AC-01, AC-03, AC-04, AC-05, AC-06, AC-10, AC-11, AC-16, AC-17, AC-18, AC-19, AC-20]
adrs: []
sdds: []
dependencies: []
implementation_plan: plans/implementation-spec-001-p0.md
sprint_tasks: [P0-01, P0-02, P0-03, P0-04]
quality_gates: [SPEC_QUALITY_GATE]
supersedes: null
superseded_by: null
approval:
  by: Solicitante humano
  date: '2026-11-19'
  evidence: "Conversación del proyecto: «Autorizo las do desiciones.» en respuesta a la solicitud de aprobación del PRD V3 y SPEC-001 v2."
---

# SPEC-001 · Consulta financiera con evidencia verificable

**Versión 2, aprobada por el propietario.** Un analista pregunta por un dato en un PDF local y puede comprobar la respuesta abriendo la página que la respalda. El recorrido P0 se demuestra con 1–2 PDF del directorio autorizado y una pregunta cuya respuesta se haya verificado contra el original. Fuentes: [PRD V3](../docs/requirements/PRD.md), [interfaz](../docs/requirements/interface_design.md) y [arquitectura](../docs/architecture/SYSTEM_ARCHITECTURE.md).

## Recorrido y contratos

1. PyMuPDF lee los originales en solo lectura. SQLite persiste texto y fragmentos por documento y página en un directorio de estado separado. El identificador deriva del contenido y la búsqueda usa FTS5 y BM25 ascendente.
2. Un agente acotado usa `search_corpus` y `read_source` con contratos Pydantic. Verifica que cada cita corresponde a evidencia leída. Con evidencia insuficiente se abstiene. La inferencia real requiere un proveedor de backend autorizado.
3. FastAPI expone salud, `POST /api/chat` con `message` y respuesta JSON con `answer`, `citations`, `warnings`, `tools_used` y `request_id`. Cada cita incluye `doc_id`, `filename`, `pdf_page`, `evidence_id` y `snippet`. La página pública empieza en 1. Solo el adaptador PyMuPDF convierte al índice desde 0.
4. En React/Vite/TypeScript, el clic en una cita abre la imagen original mediante `GET /api/documents/{doc_id}/pages/{pdf_page}/image`. Al cerrar el visor se conserva la conversación y el foco vuelve a la cita.

## Límites operativos

El usuario consulta documentos autorizados por ID. Se limitan llamadas, tiempo del agente y resolución de imagen. Una herramienta o un proveedor fallido se presenta como error recuperable. Un doble de proveedor permite probar el contrato, con identificación explícita del modo en la evidencia. El contenido de un PDF se trata como datos. Los logs omiten credenciales, texto sensible y razonamiento privado. En Coder se usa el corpus presente en `~/data`, sin descargas. Presupuesto de referencia: 2 CPU y 4 GB de RAM.

El primer corte entrega chat, evidencia, visor, README reproducible y diagrama lógico inicial. Tablas bajo demanda, cálculos Decimal, advertencias de comparabilidad y cobertura ampliada conservan su lugar en V3. Embeddings y demás ampliaciones condicionales se evaluarán en su fase. La base SQLite P0 es un derivado reconstruible. La recuperación de un fallo usa un estado de ensayo separado, preservando los originales.

## Criterios de aceptación

| Criterio | Entrada y comprobación observable | Prueba |
|---|---|---|
| SPEC-001-AC-01 | Una cita a la página 2 de un PDF con tres páginas distinguibles abre la segunda página del mismo documento. El visor funciona a 375 px. | AC-16/20, T-09/T-12, comprobación visual contra el original |
| SPEC-001-AC-02 | ID desconocido o página fuera de rango devuelve 4xx sin rutas locales. La UI permite cerrar el error o reintentar. | AC-17, T-09 |
| SPEC-001-AC-03 | Una consulta sin respaldo produce abstención. Una referencia inventada del proveedor se descarta y no llega al visor. | AC-11/18, T-08 y evaluación fuera del corpus |
| SPEC-001-AC-04 | Una segunda ingesta de los mismos PDF conserva el conteo de documentos/fragmentos y los SHA-256 de los originales. | AC-01/03/10, T-01/T-02 |
| SPEC-001-AC-05 | La consulta recupera un fragmento conocido aun con acentos. Símbolos financieros no rompen MATCH y el ranking BM25 sigue orden ascendente. | AC-04/05/06, T-03/T-04 |
| SPEC-001-AC-06 | De una pregunta en el chat se obtiene una respuesta respaldada por evidencia leída con herramientas reales. Se identifica el modo de proveedor. Si cae o agota su presupuesto, el proceso termina y la UI informa el fallo. | AC-19, T-09/T-10, smoke de extremo a extremo y caso de fallo |

## Historial y revisión

2026-11-19 · Codex registró v1 como DRAFT con los tres criterios del visor. La v2 conserva sus identificadores y abarca el recorrido completo solicitado. El propietario confirmó la arquitectura V3 y pidió presentar el PRD y esta spec antes de implementar. Aprobación funcional pendiente; pruebas de aplicación en NOT RUN. [Trazabilidad](../docs/quality/TRACEABILITY_MATRIX.md)

2026-11-19 · IN_REVIEW → APPROVED. El solicitante aprobó funcionalmente el PRD V3 y SPEC-001 v2 en la conversación del proyecto. La posterior autorización de publicar en main incluye únicamente CI y el código P0 verificado, sin originales RCTF.

2026-11-19 · APPROVED → IN_PROGRESS → IMPLEMENTED. Codex ejecutó P0-01 a P0-04. Los seis criterios cuentan con evidencia técnica en la [bitácora](../docs/execution/EXECUTION_LOG.md), incluido cotejo independiente de una página real.
