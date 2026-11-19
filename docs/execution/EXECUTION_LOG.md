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
