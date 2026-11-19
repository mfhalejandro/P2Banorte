---
name: internal-code-security
description: Revisar cambios de código en entradas, resolución de rutas, consultas, render PDF, registros o herramientas del agente.
---

# internal-code-security

Identifica entrada no confiable, validación y recurso alcanzable en el diff. Usa [restricciones y T-11](../../../docs/requirements/professionals_task.md). Comprueba IDs de catálogo, rutas resueltas bajo la raíz permitida, consultas parametrizadas y límites de páginas, DPI, bytes y tiempos. Trata texto de PDF como datos y revisa que las tools carezcan de SQL o shell abiertos.

Para cada límite modificado usa fixtures locales autorizados. Comprueba rechazo o degradación y ausencia de rutas, secretos o trazas privadas en la respuesta. Registra componente, impacto, corrección, prueba y riesgo residual. Escala al skill de seguridad de información cuando cambie el destino o clasificación de los datos.
