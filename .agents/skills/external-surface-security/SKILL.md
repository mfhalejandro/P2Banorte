---
name: external-surface-security
description: Verificar exposición, autenticación y configuración observable de una superficie desplegada dentro del alcance autorizado.
---

# external-surface-security

Exige identificación del entorno, URL y propietario, alcance, ventana y autorización de revisión según [estándar](../../../docs/requirements/estandar_arnes_nativo_ingenieria.md) §§7 y 10.3. En staging comprueba la SDR y el digest desplegado. Sin objetivo autorizado, limita el trabajo a configuración y contratos locales.

Revisa inventario de rutas expuestas, TLS, cabeceras, política de orígenes, mensajes de error y separación de controles administrativos. Comprueba el comportamiento esperado con solicitudes ordinarias y usuarios de prueba autorizados. Registra entorno, configuración, observación redactada y corrección verificable. Detén comprobaciones activas fuera de la ventana o ante efectos imprevistos.
