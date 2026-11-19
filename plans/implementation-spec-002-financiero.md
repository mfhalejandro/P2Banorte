# Plan local de SPEC-002 v1

**2026-11-19 · Responsable: Codex.** Baseline P0 en `4620231`, propuesta aprobada sobre `2898871`. Las tres pruebas preparatorias del doble P0 pasaron. La aprobación cubre AC-01 a AC-05 en local. AC-06 queda pendiente de autorización independiente. [Spec](../specs/SPEC-002-comparacion-financiera.md) · [Diseño local](../docs/architecture/sdd/SDD-002-comparacion-local.md)

| Tarea | Implementación y verificación | Dependencia |
|---|---|---|
| F-01 | Añadir verificación de procedencia y aritmética Decimal con pruebas de diferencias, escala, tasas y abstenciones. | Spec aprobada |
| F-02 | Reutilizar FTS5; recuperar periodos por separado, leer tablas bajo demanda y reconstruir las citas verificadas. Probar encabezados y celdas ambiguos. | F-01 |
| F-03 | Conectar las herramientas tipadas al agente local mediante un doble inyectable. Verificar presupuesto, errores y compatibilidad P0. | F-01/F-02 |
| F-04 | Medir con corpus sintéticos distintos, ensayar una ampliación local y documentar la demo y las limitaciones. | F-03 |

El índice de P0 es compatible sin migración. El ensayo que amplía el corpus usa un estado separado. Para volver al comportamiento P0 se selecciona `LLM_PROVIDER=extractive` y su estado habitual. El protocolo de un proveedor real se diseñará cuando exista una elección autorizada.
