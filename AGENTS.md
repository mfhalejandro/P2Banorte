# Trabajar en P2Banorte

Al iniciar o reanudar, lee el [protocolo](docs/execution/PROTOCOL.md), ejecuta el control de integridad y consulta el [estado de la etapa](docs/execution/PROGRESS.md). Trabaja desde la raíz Git. Los originales de `docs/requirements/**` son de lectura exclusiva para todo agente, herramienta y subagente. Mantén temporales y derivados fuera de esa carpeta.

Elige el procedimiento por la decisión que debes tomar. Abre el enlace directamente si tu agente carece de descubrimiento de skills. Una tarea puede cruzar dos capas. Carga la segunda guía cuando la evidencia conduzca a ella.

| Tarea | Procedimiento |
|---|---|
| Iniciar o reanudar trabajo, recibir requisitos nuevos o resolver discrepancias de la entrega humana | [rctf-preflight](.agents/skills/rctf-preflight/SKILL.md) |
| Diseñar o mantener una funcionalidad, corregir una regresión o coordinar la implementación de una especificación | [superpowers-development](.agents/skills/superpowers-development/SKILL.md) |
| Desarrollar o diagnosticar descubrimiento de PDF, ingesta, FTS5, ranking, tablas y localización de páginas | [rag-corpus-retrieval](.agents/skills/rag-corpus-retrieval/SKILL.md) |
| Desarrollar o revisar las herramientas del agente financiero, la comparabilidad de cifras y el respaldo documental de respuestas | [financial-agent-evidence](.agents/skills/financial-agent-evidence/SKILL.md) |
| Modificar o revisar chat, citas, visor de páginas, estados de interfaz o accesibilidad responsive | [responsive-frontend](.agents/skills/responsive-frontend/SKILL.md) |
| Revisar cambios de código en entradas, resolución de rutas, consultas, render PDF, registros o herramientas del agente | [internal-code-security](.agents/skills/internal-code-security/SKILL.md) |
| Evaluar cambios de proveedor, clasificación de información, permisos o límites de confianza de agentes y servicios | [information-security-audit](.agents/skills/information-security-audit/SKILL.md) |
| Verificar exposición, autenticación y configuración observable de una superficie desplegada dentro del alcance autorizado | [external-surface-security](.agents/skills/external-surface-security/SKILL.md) |
| Actualizar documentación derivada, decisiones, trazabilidad y evidencia al cambiar requisitos, contratos o estado del producto | [product-documentation](.agents/skills/product-documentation/SKILL.md) |
| Preparar revisión Git, entrega a Gitea, solicitud de staging, promoción de artefactos o cambios operativos de costo y acceso | [release-governance](.agents/skills/release-governance/SKILL.md) |

Consulta la [matriz de autorización](docs/security/AUTHORIZATION_MATRIX.md) ante una decisión reservada. Si falta una autorización o dos fuentes vinculantes discrepan, registra el impacto y pregunta al humano por la decisión concreta. Continúa el trabajo independiente autorizado.

Cierra con alcance, estado VERIFIED/PARTIAL/BLOCKED, prueba y resultado PASS/FAIL/NOT RUN, riesgos pendientes y próxima acción según el [formato de entrega](docs/requirements/format_profesional.md). Comprueba la integridad tras cada tarea y antes de integrar o cerrar.
