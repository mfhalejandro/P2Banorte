# Bitácora de ejecución

## 2026-11-19 · Implementación del arnés

Fuente: plan aceptado y confirmación humana de la entrega de 8 Markdown y 24 PDF. Responsable de ejecución: agente Codex. El solicitante autorizó implementar el arnés. La aprobación funcional del PRD sigue pendiente.

- Preflight de solo lectura: 32 archivos, 1 subdirectorio, huella idéntica a la confirmada, indicador de montaje de solo lectura activo y cero rutas escribibles. El sandbox ordinario rechazó la creación de un archivo raíz con EROFS. En el contexto autorizado se comprobó nuevamente la protección y se creó, leyó y retiró un archivo temporal en la raíz, exit 0.
- Desarrollo aislado con Python 3.12.3 y Git 2.43.0. `python3 -B -m unittest discover -s tests/harness -v`: 8 pruebas pasaron, exit 0, 1.466 s en la primera ejecución. Cada prueba Git usa un repositorio desechable. El validador local de skill-creator aceptó los diez skills (exit 0).
- Recorrido de mantenimiento: ante una cita desplazada, AGENTS dirige a responsive-frontend para verificar respuesta, enlace, petición y página. Si la respuesta ya trae el número incorrecto, rag-corpus-retrieval verifica la conversión de página. La evidencia esperada es T-09/AC-16 con el mismo par documento y página. Recorrido documental; la UI está pendiente.
- Recorrido financiero: financial-agent-evidence exige verificar ambos tipos de periodo, entidad, unidad y fuentes. Un trimestre contra un acumulado produce rechazo de la operación y abstención documentada en T-07/T-08. Recorrido documental; la calculadora está pendiente.
- Recorrido Git: release-governance conduce al manifiesto, a las capas de Git y al responsable humano. Un ZIP en el índice bloquea la entrega incluso si falta del árbol. El gate no modifica el índice.

Las pruebas funcionales del RAG, UI, integraciones externas y despliegues están en NOT RUN.

### 2026-11-19T19:59:19+01:00 · Verificación desde la raíz del proyecto

Se instalaron 26 archivos. La comprobación local resolvió los 44 enlaces Markdown y encontró las diez entradas de skill.

| Comando | Contexto | Resultado |
|---|---|---|
| `python3 -B scripts/quality/check_requirements.py --preflight` | Escritura en raíz autorizada, requisitos en montaje de solo lectura | PASS integridad, aislamiento y escritura temporal en raíz, exit 0 |
| `python3 -B -m unittest discover -s tests/harness -q` | Raíz instalada, fixtures en directorios temporales | PASS, 8 pruebas en 1.406 s, exit 0 |
| `python3 -B scripts/security/check_publication.py` | Árbol, índice real, repositorio sin primer commit | FAIL esperado, exit 1. Único hallazgo: índice, `docs/requirements.zip` |
| `git status --short` | Inspección final | Archivos nuevos del arnés sin preparar. Persisten los dos cambios iniciales del índice. |

Cierre de etapa: VERIFIED para el arnés local. PREPARADO / NO PUBLICADO. Decisiones pendientes: aprobación funcional del PRD y resolución humana del ZIP antes de publicación.

## 2026-11-19 · Corrección de la estructura documental

El solicitante señaló la ausencia de ADR, specs, SDD, planes y sprints y ratificó el estándar canónico. Se materializan las rutas de §§2, 6.2–6.3, 7.9 y 13. ADR-001 registra la elección humana del formato portable. SDD-001 describe los controles implementados en 816e4ba. SPEC-001 abre un borrador para revisar AC-16/17/18. La corrección documental del arnés se acoge a §13.3; el producto conserva su gate antes de implementación.

El preflight del contexto autorizado comprobó aislamiento, huella y escritura temporal en la raíz (exit 0). Al comenzar, el árbol y el índice estaban limpios y el gate de publicación pasó. El registro histórico del hallazgo anterior del ZIP se conserva arriba.

2026-11-19T20:08:08+01:00 · Verificación local desde la raíz: `python3 -B scripts/quality/check_specs.py` pasó para SPEC-001 y se comprobó el rechazo de ID duplicado, estado divergente y criterio sin trazabilidad. Se resolvieron los 71 enlaces de los documentos modificados. `python3 -B -m unittest discover -s tests/harness -q` pasó 8 pruebas en 2.253 s. Integridad RCTF, control automático de publicación y `git diff --check` terminaron con exit 0. Workflow remoto y pruebas funcionales de aplicación: NOT RUN.

## 2026-11-19T20:16:47+01:00 · Inicio de preparación de aplicación V3

Codex recuperó main en 13c659c. El preflight en la raíz autorizada pasó integridad, aislamiento y prueba temporal de escritura. El solicitante ratificó la arquitectura V3. El PRD de la entrega confirmada (SHA-256 7c66a68dbd121430cffbf16c6b637b8e0e69cdf2cbd655bcec70e1eed19eff0b) y SPEC-001 v2 se presentan para decisión funcional. Se conservan los tres criterios de v1 y se añaden ingesta, recuperación y agente al alcance del primer recorrido. Plan y tareas en preparación, pruebas del producto NOT RUN.

CI: en la [ejecución de GitHub](https://github.com/mfhalejandro/P2Banorte/actions/runs/44595451678), el job specs 135812375814 terminó con exit 1 en la referencia al PRD. El mismo fallo se reprodujo desde git archive de ese SHA. La corrección del workflow y del verificador pasó en un checkout limpio sin originales, usando únicamente el inventario confirmado. Las pruebas negativas rechazaron un Markdown privado ausente del inventario, un enlace de arquitectura roto, la entrega local ausente y una entrega parcial en modo CI. La validación del checkout no representa una aprobación funcional ni una ejecución remota del cambio.

Verificación final en el repositorio: preflight, spec en modo local estricto, diff --check, frontera de publicación y 8 pruebas del arnés pasaron. En un clon limpio de 13c659c se aplicaron únicamente los tres archivos de la corrección CI: el comando del workflow pasó también con la spec original v1, sin copiar requisitos ni incorporar el trabajo P0. Aprobación de producto y ejecución remota del cambio pendientes al registrar esta evidencia.

## 2026-11-19 · Aprobación e inicio de construcción

El solicitante aprobó el PRD V3 de la entrega confirmada y SPEC-001 v2 con «Autorizo las do desiciones.». Autorizó expresamente publicar CI y código P0 verificado en main sin originales RCTF. La rama temporal superó [Spec quality](https://github.com/mfhalejandro/P2Banorte/actions/runs/44597404997) en 3765a15.

### Verificación técnica del corte P0 · 2026-11-19

Se probaron las superficies del plan con Python 3.12, SQLite FTS5, React 19, Vite 7 y Chromium local. El agente usó el modo extractivo local, con búsqueda y lectura reales. Inferencia generativa externa: NOT RUN por falta de proveedor autorizado. Los originales, sus imágenes, el índice, entornos de dependencias y logs crudos quedan fuera de Git.

| Evidencia | Comando o recorrido | Resultado |
|---|---|---|
| P0-01 | Ingesta con `python -m apps.api.corpus --limit 2` y repetición | 24 PDF descubiertos, 2 indexados. Segunda ejecución: 2 reutilizados, 0 nuevos, 0 fallidos. |
| P0-01/02/03 | `python -m pytest -q tests/p0 tests/harness` | 15 pruebas pasaron en 5.87 s, además de 5 subcasos. Un aviso de deprecación del cliente de pruebas de Starlette. |
| P0-03 | `npm run build` | TypeScript y compilación de assets de desarrollo verificados, exit 0. |
| P0-03/04 | `npm run smoke`, servidores y PDF ficticio en loopback | 6 pruebas pasaron en 12.5 s. Cita a la página 2 en 320, 375, 768, 1024 y 1440 px, foco restaurado, error de fuente, reintento y abstención. |
| P0-04 | Consulta real «¿Qué es el riesgo de crédito?» en navegador a 375 px | Respuesta extractiva sobre incumplimiento de obligaciones de pago; la cita abrió la página 7 del mismo documento. Se cotejó el texto con pdftotext ejecutado sobre esa página del original y se comprobó la decodificación del PNG. |

Los límites del primer corte y el procedimiento de reproducción están en el [README](../../README.md).
