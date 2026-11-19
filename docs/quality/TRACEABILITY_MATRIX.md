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

## Siguiente corte · SPEC-002 v1

| Requisito | Criterio | Prueba prevista | Estado |
|---|---|---|---|
| PRD AC-19 y AC-21 | SPEC-002-AC-01 | T-10/T-11, ciclo con doble local | NOT RUN |
| PRD AC-07/09/16/18 | SPEC-002-AC-02 | T-05/T-06 y apertura dirigida de ambas citas | NOT RUN |
| PRD AC-11 a AC-15 | SPEC-002-AC-03 | T-07/T-08, comparación Decimal y abstenciones | NOT RUN |
| PRD AC-02/03/08/10/25–27 | SPEC-002-AC-04 | T-02/T-13/T-14/T-16, dos corpus y ampliación gradual | NOT RUN |
| PRD AC-16/18/19 | SPEC-002-AC-05 | T-09 si cambian interfaz o código compartido con P0 | NOT RUN |
| PRD AC-19 y AC-21 | SPEC-002-AC-06 | T-10, ciclo sintético con proveedor real autorizado | NOT RUN, autorización independiente pendiente |
