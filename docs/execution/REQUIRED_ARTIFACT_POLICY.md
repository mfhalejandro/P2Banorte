# Cuándo abrir o actualizar un artefacto

Aplica la matriz completa de [§7.9 del estándar](../requirements/estandar_arnes_nativo_ingenieria.md). Usa las rutas siguientes para los artefactos de diseño y ejecución de esta etapa.

| Evento | Documento canónico | Condición de salida |
|---|---|---|
| Elección material de tecnología, proveedor o topología | [ADR](../adr/README.md) | Alternativas, consecuencias, propietario y decisión registradas |
| Cambio de comportamiento, contrato, datos o seguridad | [Spec](../../specs/README.md) | Criterios medibles, trazabilidad, revisión y aprobación aplicables |
| Diseño complejo de una solución aprobada | [SDD](../architecture/sdd/README.md) | Interfaces, secuencias, fallos y verificaciones documentados |
| Spec aprobada lista para descomposición | [Plan](IMPLEMENTATION_PLAN.md) | Versiones de fuentes, dependencias, archivos y pruebas identificados |
| Plan que requiere capacidad, responsables y seguimiento temporal | [Sprint](SPRINTS.md) | Tareas, ventanas y evidencia por criterio |

Cuando cambien exposición, operación, migraciones, ambiente, costos o permisos, genera el artefacto correspondiente de §7.9 en la fase afectada. La creación del documento y su aprobación son actos separados.
