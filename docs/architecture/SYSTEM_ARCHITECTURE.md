# Arquitectura del sistema

**Versión 1 · 2026-11-19 · Síntesis técnica de Codex.** El arnés local existe. La arquitectura de aplicación que sigue es el objetivo V3 del [PRD](../requirements/PRD.md) y del [stack](../requirements/technology_stack.md), pendiente de aprobación funcional e implementación.

| Capa de la aplicación prevista | Responsabilidad y límite |
|---|---|
| React/Vite | Capturar la pregunta, representar respuestas y abrir citas por documento y página. |
| FastAPI y agente | Validar contratos y límites de herramientas. Acceder a inferencia únicamente mediante un proveedor autorizado. |
| Ingesta y recuperación | Leer PDF locales con PyMuPDF. Mantener SQLite FTS5 y cachés fuera del corpus. Recuperar páginas para citas y tablas bajo demanda. |
| Evidencia y cálculo | Relacionar fuente, página, periodo y unidad antes de calcular con Decimal o abstenerse. |

El arnés controla el trabajo mediante RCTF, permisos, skills bajo demanda y dos verificadores locales. Para sus interfaces y modos de fallo, consulta el [SDD del arnés](sdd/SDD-001-controles-locales.md). Para decisiones materiales consulta el [índice ADR](../adr/README.md).
