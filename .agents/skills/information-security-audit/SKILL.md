---
name: information-security-audit
description: Evaluar cambios de proveedor, clasificación de información, permisos o límites de confianza de agentes y servicios.
---

# information-security-audit

Dibuja el flujo afectado desde corpus, pregunta y evidencia hasta almacenamiento, logs y proveedor. Identifica finalidad, clasificación, identidad y autorización por destino según el [estándar](../../../docs/requirements/estandar_arnes_nativo_ingenieria.md) §§6.4, 10.1 y 15. Acceso local de lectura y autorización para comunicar datos a terceros se verifican por separado.

Revisa minimización, redacción, retención, segregación por ambiente y permisos efectivos. Para una elevación abre PCR con identidad, recurso, permiso mínimo, expiración y revocación, con aprobación independiente. Registra decisión, riesgo y evidencia sanitizada. Si un destino carece de autorización, detén ese flujo y usa fixtures locales para la revisión permitida.
