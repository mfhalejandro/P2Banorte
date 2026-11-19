# SDD-001 · Verificación de requisitos y candidatos Git

**Versión 1 · 2026-11-19 · Autor: Codex.** Documento retrospectivo del arnés existente en `816e4ba`. El encargo y el [ADR-001](../../adr/ADR-001-arnes-portable.md) gobiernan esta etapa. Este registro describe la implementación observada y queda disponible para revisión humana.

| Control | Entradas y secuencia | Salida y recuperación |
|---|---|---|
| [Integridad](../../../scripts/quality/check_requirements.py) | Leer el manifiesto confirmado, inventariar archivos y directorios, calcular SHA-256 y comprobar protección efectiva. Con `--preflight`, probar la raíz después de validar las fuentes. | Exit 0 habilita el trabajo local dentro del alcance. Con exit 1, investigar entrega o aislamiento. El humano resuelve una sustitución. |
| [Frontera Git](../../../scripts/security/check_publication.py) | Leer manifiesto de publicación y examinar árbol candidato, entradas staged y snapshots de los commits salientes. La revisión usa los objetos Git del índice y del historial incluso cuando falta el archivo local. | Exit 1 identifica capa, ruta y clase de hallazgo. Exit 0 permite continuar con revisión humana de derechos y contenido. |

Los dos controles se ejecutan localmente. El primero mantiene la línea base y los derivados fuera de los originales. El segundo no cambia el índice. Una nueva entrega humana requiere confirmación explícita antes de sustituir la línea base activa. Las [pruebas del arnés](../../../tests/harness/test_controls.py) cubren alteración de inventario, reemplazo por enlace y contenido restringido en índice o historial. El despliegue y rollback de una aplicación quedan fuera de estos ejecutables locales.
