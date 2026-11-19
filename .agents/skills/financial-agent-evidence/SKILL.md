---
name: financial-agent-evidence
description: Desarrollar o revisar las herramientas del agente financiero, la comparabilidad de cifras y el respaldo documental de respuestas.
---

# financial-agent-evidence

Consulta [contexto financiero](../../../docs/requirements/context_for_the_professional.md) §§3 y 7 y [contratos técnicos](../../../docs/requirements/technology_stack.md) §§4–5. Traza pregunta, herramientas permitidas, evidencias y salida pública. Conserva límites de pasos y tiempo en reintentos. Un proveedor de programación disponible en el IDE requiere autorización y verificación independientes para el backend.

Para cada operando comprueba `source_id`, documento, página, entidad, periodo, tipo de periodo, unidad, moneda, escala y encabezado de celda. Identifica notas de reexpresión y cambios de perímetro como Bineo. Una coincidencia textual aislada no acredita el valor. Si falta respaldo, devuelve el estado de procedencia y explica la abstención. Calcula con `Decimal`, verifica denominador y distingue puntos porcentuales de variación relativa.

Prueba una comparación respaldada y otra entre trimestre y acumulado que deba rechazarse. Verifica además fuente inexistente, presupuesto agotado y caída del proveedor cuando afecte al cambio. Registra T-05/T-07/T-08/T-10 según corresponda, con el modo real o simulado y sin razonamiento privado.
