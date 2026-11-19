---
name: superpowers-development
description: Diseñar o mantener una funcionalidad, corregir una regresión o coordinar la implementación de una especificación.
---

# superpowers-development

Parte de [tareas y pruebas](../../../docs/requirements/professionals_task.md) y [estado actual](../../../docs/execution/PROGRESS.md). Para un defecto, reproduce el comportamiento con una prueba dirigida y comprueba si el contrato aprobado ya lo cubre. Para un cambio observable o material, prepara una spec con identificador permanente, metadatos, límites y criterios verificables según el estándar §13. Crea plantilla y registro en `specs/` al activar esa fase. Registra un ADR si se decide entre alternativas materiales y un SDD si el diseño detallado lo exige. Vincula la spec aprobada al plan y las pruebas antes de implementar.

Trabaja en development. En P0 prueba pronto el recorrido pregunta → página original. Acota el cambio, ejecuta la prueba dirigida y revisa el diff con sus dependencias. Si falla, conserva la reproducción y localiza primero la capa que rompe el contrato.

Si la delegación está autorizada y aporta aislamiento, crea los contratos y registros de §12 antes de delegar. Asigna un solo escritor por superficie, archivos permitidos, fuentes, pruebas, plazo y condición de parada. El principal verifica A1 sobre la tarea y A2 sobre la integración, reúne evidencia independiente y reconcilia progreso y bitácora. Consulta la [admisión de herramientas](../../../docs/execution/TOOLCHAIN.md) antes de invocar Superpowers.
