# SDD-002 · Herramientas y procedencia en el corte local

**v1 · 2026-11-19 · Codex.** Diseño del tramo local aprobado mediante [SPEC-002 v1](../../../specs/SPEC-002-comparacion-financiera.md). Extiende el monolito y el esquema SQLite de P0. La conexión real corresponde a AC-06.

- El modo de comparación local recibe la misma solicitud de chat. Un proveedor determinista propone llamadas tipadas y recibe resultados. El agente limita llamadas y tiempo y ejecuta solo las cinco herramientas conocidas. La calculadora y las citas proceden del backend.
- Búsqueda y catálogo comparten el índice existente. La lectura de evidencia abre el original por SHA y restringe la inspección a páginas candidatas. La procedencia validada vive solo durante la solicitud. Un número en una fila equivocada carece de autoridad para apoyar la operación.
- El cálculo recibe posiciones de evidencia verificadas, contrasta tipo y duración, entidad, moneda, unidad y base, y devuelve una explicación para los casos no resolubles. El visor vigente consume las mismas referencias por documento y página.
- Banco de pruebas local con tablas generadas y doble inyectado. El modo extractivo sigue separado. Una ejecución interrumpida conserva el último índice completo y la demo de ampliación usa otro estado. [Plan y pruebas](../../../plans/implementation-spec-002-financiero.md)
