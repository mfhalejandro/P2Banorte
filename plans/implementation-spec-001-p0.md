# Preparación del primer corte P0

**Plan activo · SPEC-001 v2 · 2026-11-19 · Codex.** El propietario aprobó el PRD V3 y la [especificación](../specs/SPEC-001-cita-pdf.md). Se conserva el monolito modular V3. El flujo y sus interfaces ya están definidos en la spec y la arquitectura vigente.

| Orden | Superficie | Trabajo y evidencia de salida |
|---|---|---|
| P0-01 | Ingesta y almacenamiento | Con 1–2 PDF pequeños, descubrir, identificar por hash, extraer páginas y persistir SQLite FTS5 fuera del corpus. Obtener conteos estables en reingesta y SHA de originales idénticos. |
| P0-02 tras P0-01 | Recuperación, herramientas y agente | Buscar un pasaje conocido, leer la página y validar procedencia. Acotar pasos y tiempo. Probar abstención, fallo de proveedor y cita desconocida con un doble identificado. |
| P0-03 desde el contrato, integración tras P0-02 | FastAPI y React | Preparar chat y visor desde el inicio. Exponer salud, respuesta JSON e imagen PNG por ID/página. Comprobar error 4xx, móvil y retorno de foco. |
| P0-04 tras integración | Smoke, README y diagrama | Desde estado de ensayo nuevo, ejecutar ingesta → pregunta → respuesta → clic → cotejo con original. Registrar consulta, doc_id, página, modo del proveedor, recursos y resultados. |

Usar fixtures locales con páginas distinguibles para regresión y un PDF de ensayo autorizado para la demo. Si falta inferencia programática autorizada, verificar los contratos y la recuperación con doble y dejar el smoke de inferencia real pendiente. El estado de prueba se puede reconstruir en otra carpeta. Un fallo en la cita impide cerrar el corte. [Asignación y estado](../docs/execution/SPRINTS.md)
