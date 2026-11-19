# Gate de especificaciones

Desde la raíz ejecuta `python3 scripts/quality/check_specs.py` con PyYAML 6 instalado. El control local y el workflow spec-quality usan el mismo comando. Comprueban identificadores únicos, metadatos, estado, coherencia con el registro y trazabilidad, enlaces de la spec y evidencia declarada al pasar de borrador a aprobación. Exit 1 bloquea el avance.

El revisor contrasta resultado, alcance, contratos, permisos, compatibilidad y criterios medibles contra el PRD y las decisiones aplicables. Revisa el historial de transiciones y verifica la autenticidad y vigencia de la aprobación en la [matriz de autorización](../security/AUTHORIZATION_MATRIX.md). Registra dependencias, pruebas, operación, costos y riesgos cuando apliquen. Un control automático correcto con estado DRAFT permite revisar el documento. La implementación exige aprobación humana verificable de la versión y los demás controles de entrada de [§13.11–13.12](../requirements/estandar_arnes_nativo_ingenieria.md).

Para ejecutar este gate desde un checkout de CI, la entrega humana debe hacer accesibles los Markdown RCTF referenciados. Si una referencia falta, la comprobación falla y muestra la ruta. El agente no incorpora los originales al índice para resolver ese fallo.
