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
