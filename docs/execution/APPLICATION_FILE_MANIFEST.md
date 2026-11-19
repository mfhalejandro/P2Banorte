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
| `docs/adr/*.md` | Decisiones y alternativas | Proyecto, revisión de contenido | Revisar entrega |
| `specs/*.md` | Especificaciones, registro y archivo | Proyecto, revisión de contenido | Revisar entrega |
| `docs/architecture/*.md` | Arquitectura y diseños detallados | Proyecto, revisión de contenido | Revisar entrega |
| `plans/*.md` | Planes de implementación | Proyecto, revisión de contenido | Revisar entrega |
| `docs/plans/*.md` | Acceso documental a planes | Proyecto, revisión de contenido | Revisar entrega |
| `docs/sprints/*.md` | Programación por sprint | Proyecto, revisión de contenido | Revisar entrega |
| `.github/workflows/spec-quality.yml` | Validación de specs, permiso de lectura | Proyecto, revisión de contenido | Revisar entrega |
| `README.md` | Arranque, límites y reproducción del P0 | Proyecto P0, código o metadatos revisables | Entrega autorizada en main |
| `pyproject.toml` | Dependencias Python del P0 | Proyecto P0, código o metadatos revisables | Entrega autorizada en main |
| `uv.lock` | Versiones y hashes de las distribuciones Python | Proyecto P0, código o metadatos revisables | Entrega autorizada en main |
| `apps/api/*.py` | Ingesta, agente y API locales | Proyecto P0, código o metadatos revisables | Entrega autorizada en main |
| `apps/web/*.json` | Metadatos, compilación y lock de dependencias web | Proyecto P0, código o metadatos revisables | Entrega autorizada en main |
| `apps/web/*.ts` | Configuración y pruebas TypeScript | Proyecto P0, código o metadatos revisables | Entrega autorizada en main |
| `apps/web/src/*.tsx` | Interfaz de chat y visor | Proyecto P0, código o metadatos revisables | Entrega autorizada en main |
| `apps/web/src/*.css` | Estilos de la interfaz | Proyecto P0, código o metadatos revisables | Entrega autorizada en main |
| `apps/web/index.html` | Entrada del cliente web | Proyecto P0, código o metadatos revisables | Entrega autorizada en main |
| `tests/p0/*.py` | Pruebas y generador de PDF ficticios | Proyecto P0, código o metadatos revisables | Entrega autorizada en main |
| `tests/financial/*.py` | Pruebas y generador local de PDF ficticios del corte financiero | Proyecto, código o fixtures generados | Revisión para eventual entrega |

Revisar rutas adicionales al ampliar la aplicación. Mantener fuera de entrega los secretos, bases, corpus operativo, archivos comprimidos y PDF reales sin permiso específico.
