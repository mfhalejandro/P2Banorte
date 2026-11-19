---
name: release-governance
description: Preparar revisión Git, entrega a Gitea, solicitud de staging, promoción de artefactos o cambios operativos de costo y acceso.
---

# release-governance

Para Git sigue el [gate de publicación](../../../docs/quality/REPOSITORY_BOUNDARY_GATE.md). Identifica rama, destino y commits salientes. Revisa también archivos que solo existen en el índice o en un commit anterior. El solicitante incorpora los requisitos a Git y aprueba la publicación que corresponda.

Para staging prepara SDR-NNN con commit, alcance, pruebas, datos, configuración, costo y rollback. Espera aprobación antes de compilar la imagen candidata. Para producción registra digest ya probado en staging, SBOM, evidencia, estimación aprobada y responsable del rollback. El reto pide un diagrama cloud y cualquier despliegue real requiere encargo y autorización propios.

Para un costo prepara estimación con escenarios y libro append-only por cost_item_id evitando doble conteo. Para un permiso usa PCR con vigencia, revisión y revocación. Usa las plantillas y gates de las secciones 7 y 15 del [estándar](../../../docs/requirements/estandar_arnes_nativo_ingenieria.md) al activarse el flujo. Cierra indicando autorización efectiva, acciones realizadas y lo pendiente.
