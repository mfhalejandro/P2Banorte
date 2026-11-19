# Frontera de publicación

Ejecuta primero el gate de integridad. Desde la raíz usa `python3 scripts/security/check_publication.py`. Revisa candidatos del árbol según Git, archivos rastreados, todas las entradas del índice y cada árbol del historial alcanzable desde HEAD. Los archivos locales ignorados y sin seguimiento quedan fuera del conjunto que Git publicaría. El script no prepara cambios. Sin primer commit examina árbol e índice.

Para una entrega identifica el remoto Gitea SSH y la referencia exacta a enviar. Verifica que HEAD sea la punta de esa referencia. Si se conoce el ancestro remoto, usa `--base <SHA-verificado>`. Para varias referencias o etiquetas revisa por separado todos los objetos salientes, incluidos mensajes y adjuntos, o bloquea la entrega si queda contenido sin inspeccionar.

Código 1 bloquea por material restringido, contenido sospechoso, tipo inesperado, rutas sin clasificar o verificación incompleta. Código 0 cubre solo el control automático. Revisa el diff, cambios del propio manifiesto, licencias, datos personales, mensajes de commits, autoría y clasificación antes de autorizar publicación. Si hay material prohibido solo en el índice o en historial, comunica ruta y capa sin exponer contenido. Su retirada, reescritura o publicación requieren una decisión humana separada.
