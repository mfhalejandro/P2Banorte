# Integridad de la entrega humana

Ejecuta `python3 scripts/quality/check_requirements.py` desde la raíz al iniciar, reanudar, terminar una tarea y antes de integrar, promover o cerrar. Código 0 indica inventario idéntico y protección efectiva. Código 1 bloquea escritura y exige revisión humana. Comprueba además la capacidad de escritura en el destino autorizado antes de comenzar una etapa. Mantén los montajes y permisos bajo administración humana.

La entrega del 19 de noviembre de 2026 está confirmada por el solicitante. El [manifiesto](REQUIREMENTS_INTEGRITY_MANIFEST.json) registra ruta relativa, tipo y, para archivos, tamaño y SHA-256 de bytes. El hash agregado cubre el arreglo de entradas en orden de ruta POSIX, claves ordenadas, JSON UTF-8 sin escape ASCII, sin espacios y sin salto final. Una renominación modifica la huella aunque el contenido coincida. Los enlaces inesperados bloquean el control.

Ante una nueva entrega humana, conserva el manifiesto anterior con su identidad fuera de los originales. Compara inventarios, registra cambios y pide confirmación explícita de la nueva huella antes de activar otra línea base. El verificador carece de modo para aceptar diferencias.
