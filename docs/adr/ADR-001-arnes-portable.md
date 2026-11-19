# ADR-001 · Una entrada portable y skills por tarea

**Versión 1 · 2026-11-19 · Decisión en uso.** Autor del registro retrospectivo: Codex. El solicitante eligió «Markdown portable» y autorizó implementar el plan del arnés. La elección se limita al arnés.

El equipo necesita usar Codex y agentes con mecanismos distintos de descubrimiento. Se consideraron una integración nativa adicional para Claude Code y un catálogo Markdown común. El solicitante eligió el catálogo común. El agente parte de [AGENTS.md](../../AGENTS.md) y abre el `SKILL.md` indicado por la tarea. Una sola copia por procedimiento reduce la posibilidad de instrucciones divergentes. Los clientes que carecen de autodetección dependen de que el operador les indique la entrada.

La validación comprobó los diez skills, los enlaces y tres recorridos de mantenimiento. Reabrir la decisión cuando un cliente requerido no pueda seguir ese recorrido o se solicite expresamente una integración nativa. [Evidencia](../execution/EXECUTION_LOG.md)
