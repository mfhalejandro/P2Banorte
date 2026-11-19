# Manifiesto de candidatos a publicación

El control lee los patrones de la primera columna de esta tabla. Son rutas relativas Git con glob; el comodín puede abarcar subdirectorios. Propietario de revisión: solicitante. Cada inclusión queda sujeta a revisión de contenido, licencia/procedencia y autorización para el destino. Antes de introducir otro tipo de material, clasifícalo y actualiza este manifiesto con decisión trazable.

| Patrón | Finalidad | Procedencia / clasificación | Estado |
|---|---|---|---|
| `AGENTS.md` | Entrada portable | Proyecto, evaluable | Revisar entrega |
| `.gitignore` | Política de seguimiento | Proyecto, configuración | Revisar diff |
| `.agents/skills/*/SKILL.md` | Procedimientos | Autoría local, evaluable | Revisar admisión |
| `docs/MASTER_DOCUMENT.md` | Fuentes canónicas | Proyecto | Revisar entrega |
| `docs/requirements/*.md` | RCTF para evaluación | Original humano | Incorporación humana y revisión de derechos |
| `docs/execution/*.md` | Estado y control | Proyecto, solo versiones sanitizadas | Revisar entrega |
| `docs/security/*.md` | Políticas | Proyecto, solo versiones sanitizadas | Revisar entrega |
| `docs/quality/*.md` | Gates y evidencia | Proyecto, solo versiones sanitizadas | Revisar entrega |
| `docs/quality/REQUIREMENTS_INTEGRITY_MANIFEST.json` | Identificar entrega confirmada | Metadatos derivados, revisar nombres | Revisar entrega |
| `scripts/quality/*.py` | Control de integridad | Autoría local | Revisar código |
| `scripts/security/*.py` | Control de publicación | Autoría local | Revisar código |
| `tests/harness/*.py` | Pruebas aisladas | Autoría local, fixtures sintéticos | Revisar código |

Cuando se active la aplicación, incorporar rutas de código, pruebas y documentación aprobadas. Mantener fuera de entrega los secretos, bases, corpus operativo, archivos comprimidos y PDF reales sin permiso específico.
