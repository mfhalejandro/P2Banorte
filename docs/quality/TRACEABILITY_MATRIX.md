# Trazabilidad de la entrega

| Fuente | Tarea verificable | Prueba / evidencia | Estado |
|---|---|---|---|
| Estándar §§3.11, 4, PRD AC-22 | Identificar la línea base y proteger las fuentes durante el desarrollo | Verificador RCTF, IntegrityTests, bitácora | Control del arnés disponible; prueba de aplicación pendiente |
| Estándar §14, PRD AC-23, T-15 | Detectar contenido no publicable en las superficies de Git | PublicationTests, gate sobre el índice real | Hallazgo inicial del ZIP resuelto en el índice de 816e4ba; revisión de publicación aplicable |
| Formato §3, estándar §§8–12 | Entrada portable y elección de skill | Diez frontmatters y recorridos de la bitácora | Validación local |
| PRD AC-16, T-09 · [SPEC-001-AC-01](../../specs/SPEC-001-cita-pdf.md) | Abrir la página correcta desde una respuesta | P0, prueba UI/API sobre un documento indexado | NOT RUN; producto pendiente |
| PRD AC-17, T-09 · SPEC-001-AC-02 | Rechazar referencia inválida sin exponer rutas | Prueba API/UI prevista | DRAFT, NOT RUN |
| PRD AC-18 · SPEC-001-AC-03 | Comunicar ausencia de respaldo | Evaluación de consulta fuera del corpus | DRAFT, NOT RUN |
| PRD AC-11 a AC-15, T-07/T-08 | Cálculo con operandos comparables y procedencia | Pruebas de contrato y abstención de la etapa de aplicación | NOT RUN |
| PRD AC-25/AC-26, T-16 | Descubrir corpus variable y deduplicar por contenido | Ingesta con dos conjuntos de prueba | NOT RUN |

Al aprobar una spec, añadir su identificador y plan a las filas correspondientes. Conservar referencia a la ejecución real y al cambio verificado.
