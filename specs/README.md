# Especificaciones

Parte del [PRD](../docs/requirements/PRD.md) y usa la [plantilla](SPEC_TEMPLATE.md). Reserva un ID permanente en el [registro](SPEC_REGISTRY.md), crea `SPEC-NNN-nombre.md` y enlaza los criterios con la [matriz](../docs/quality/TRACEABILITY_MATRIX.md). Conserva identificadores al renombrar y archiva versiones retiradas en [archived/](archived/README.md).

El ciclo normal es DRAFT → IN_REVIEW → APPROVED → IN_PROGRESS → IMPLEMENTED → VERIFIED. BLOCKED, REJECTED, SUPERSEDED y ARCHIVED documentan excepciones. Registra para cada transición el motivo, la fecha, la persona responsable y la evidencia. Solo el propietario autorizado aprueba. Aplica el [gate de especificación](../docs/quality/SPEC_QUALITY_GATE.md) antes de construir. Revisa de nuevo los cambios materiales a comportamiento, permisos o aceptación según [§13 del estándar](../docs/requirements/estandar_arnes_nativo_ingenieria.md).
