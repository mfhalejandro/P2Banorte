---
id: SPEC-001
title: Abrir la página original citada
version: 1
status: DRAFT
owner: Solicitante humano
reviewers: []
created_at: '2026-11-19'
updated_at: '2026-11-19'
prd_requirements: [AC-16, AC-17, AC-18]
adrs: []
sdds: []
dependencies: []
implementation_plan: null
sprint_tasks: []
quality_gates: [SPEC_QUALITY_GATE]
supersedes: null
superseded_by: null
approval: null
---

# SPEC-001 · Abrir la página original citada

**Borrador para revisión funcional.** El usuario de la consulta necesita comprobar una respuesta en el PDF local del que procede. El resultado observable es que la cita abre la página correcta o que la interfaz explica por qué carece de evidencia. Fuentes: [PRD](../docs/requirements/PRD.md), [interfaz](../docs/requirements/interface_design.md) y [arquitectura prevista](../docs/architecture/SYSTEM_ARCHITECTURE.md).

## Alcance y actores

El usuario consulta documentos disponibles en el catálogo autorizado. El backend resuelve la evidencia y la UI presenta la página. Se cubre la apertura de una cita y los fallos de referencia. El benchmarking global de recuperación, la calculadora, el despliegue cloud y la gestión de usuarios pertenecen a otros cambios.

## Flujo, interfaces y errores

La respuesta contiene el identificador del documento y su número de página PDF desde 1. Al activar una cita, la UI solicita la imagen de ese par al backend y muestra documento y página. La conversión al índice interno del parser ocurre al leer el PDF. Un ID desconocido o una página fuera de rango da un error 4xx sin rutas locales. Una respuesta sin respaldo explica la limitación y carece de citas inventadas. Eventos de streaming y cambios de esquema persistente: N/A para este contrato de vista.

## Controles y operación

El backend valida el catálogo, el rango y los límites de render. El visor lee el corpus autorizado. La respuesta pública excluye razonamiento privado y el registro técnico puede identificar la clase de error sin exponer secretos. No se supone autorización para enviar documentos a un proveedor. La evaluación cotejará la página mostrada contra una página conocida, distinguible visualmente de las contiguas. Disponibilidad y latencia se medirán en el entorno del reto antes de fijar umbrales. Migración y rollback de datos: N/A para este borrador de una superficie nueva. Si la comprobación falla, se detiene la entrega del cambio.

## Criterios de aceptación

| Criterio | Entrada y precondición | Resultado esperado | Prueba prevista |
|---|---|---|---|
| SPEC-001-AC-01 | Respuesta con una cita a la página 2 de un PDF con tres páginas distintas | Al activar la cita se muestra la segunda página del mismo documento | AC-16, T-09, comparación con original |
| SPEC-001-AC-02 | ID desconocido o página posterior a la última | El backend devuelve 4xx sin ruta local y la interfaz muestra un error recuperable | AC-17, T-09, API y UI |
| SPEC-001-AC-03 | Pregunta sin evidencia en el corpus del ensayo | La respuesta comunica insuficiencia y no ofrece referencia inventada | AC-18, evaluación con consulta fuera del corpus |

## Decisiones y evidencia

2026-11-19 · Codex redactó v1 en DRAFT al materializar el gobierno de specs. La revisión del PRD, la aprobación de este alcance y la asignación de responsables de pruebas están pendientes. Las pruebas de aplicación figuran en NOT RUN en la [matriz de trazabilidad](../docs/quality/TRACEABILITY_MATRIX.md).
