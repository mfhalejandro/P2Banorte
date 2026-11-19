# Matriz de autorizaciones

| Operación | Quién decide | Evidencia previa |
|---|---|---|
| Leer RCTF, trabajar en el arnés y ejecutar pruebas locales aisladas | Agente dentro del encargo | Alcance de la etapa, preflight y archivos permitidos |
| Cargar, sustituir o versionar originales RCTF | Solicitante humano | Nueva entrega identificada y confirmada, historial de líneas base |
| Aprobar PRD, spec o decisión material | Propietario humano | Decisión trazable, versión, fecha y alcance |
| Introducir skill o hook externo, proveedor, acceso de red o cesión de datos | Propietario y revisión de seguridad aplicable | Admisión, permisos, licencia y destino |
| Delegar si el runtime y el encargo lo permiten | Agente principal dentro de permisos concedidos | Contrato acotado, rutas de escritura, revisión independiente |
| Commit, integración, push y publicación de PDF | Titular según autorización específica | Frontera Git y derechos de redistribución por documento |
| Compilar candidato, staging y promoción | Aprobador humano del entorno | SDR aprobada para staging, digest y gates para producción |
| Gastar o elevar privilegios | Aprobador humano competente e independiente | Cotización o PCR, límite, vigencia y reversión |

Toda superficie de escritura excluye `docs/requirements/**`. Esta matriz no concede acceso técnico. Si faltan identidad o evidencia de aprobación, registra la decisión pendiente y consulta antes de la acción reservada.
