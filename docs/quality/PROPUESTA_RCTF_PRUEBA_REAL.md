# Propuesta de ajustes RCTF para la prueba real

**Pendiente de aprobación humana.** Base técnica V3 congelada. El propietario revisaría y entregaría una nueva versión de los RCTF. Las etiquetas SIM-001 a SIM-006 provienen del encargo de retrospectiva. [Evidencia posterior al cierre](AUDITORIA_FUNCIONAL_PRUEBA_REAL.md)

## Cambios propuestos

### SIM-001 · Aislamiento comprobado en el runtime real

**Destino:** estándar del arnés §3.11 y TASK §2. **Problema:** una huella correcta puede coexistir con escritura sobre los originales. Coder podría carecer del mecanismo de aislamiento del ensayo.

> Antes de habilitar escritura en el proyecto, comprueba integridad de los RCTF y PDF, acceso de solo lectura a los originales y escritura temporal fuera de ellos, desde el mismo usuario y runtime que ejecutará el trabajo. Usa montaje de solo lectura o permisos equivalentes efectivos, incluida la protección del directorio frente a sustitución. Si el entorno carece de esa garantía, suspende el trabajo con escritura y solicita al responsable que proteja los originales. El responsable puede autorizar una copia de trabajo desechable con verificación inicial y final como control compensatorio para ese trabajo aislado. Registra su alcance y clasifica por separado la protección de la fuente.

**Aceptación:** evidencia de lectura y escritura temporal en las superficies correspondientes y cotejo final del manifiesto. Una fuente escribible suspende el gate estricto aunque coincidan las huellas. **Impacto:** hasta 5 minutos de T+00 a T+15. Si falta protección, dedicar el tramo a tareas de lectura y pedir decisión.

### SIM-002 · Reanudación entre codificadores

**Destino:** ROLE §Responsabilidades del agente principal y estándar §12.8. **Problema:** cambiar de asistente o runtime puede perder permisos y atribución de cambios locales.

> Al cambiar entre Codex, OpenCode u otro codificador autorizado, el agente saliente registra SHA, referencia, cambios locales, autorizaciones vigentes, fases aprobadas, servicios y comandos verificables, pruebas pendientes y siguiente tarea acotada en los documentos de estado existentes. El entrante repite el preflight en su runtime, verifica el árbol y el índice Git, comprueba el smoke y reanuda desde la última evidencia confirmada. Las credenciales y conversaciones privadas quedan fuera del traspaso.

**Aceptación:** un segundo runtime confirma el mismo SHA y cambios locales y reproduce el smoke con el traspaso. **Impacto:** hasta 5 minutos por cambio imprescindible. Evitar cambios electivos después de T+140.

### SIM-003 · Requisitos privados y frontera Git

**Destino:** PRD §11 y RNF-11, estándar §§14.1–14.4 y FORMAT §7. **Problema:** el material canónico local y lo que el remoto puede recibir tienen autorizaciones diferentes.

> En preflight, el propietario identifica destino, referencia y artefactos autorizados. Conserva los RCTF privados y PDF en su canal autorizado de solo lectura. Su incorporación al remoto, si la evaluación la exige, requiere entrega y aprobación expresas del propietario para ese destino y revisión de derechos. Antes de publicar, revisa árbol, índice y commits salientes contra la lista positiva. Excluye PDF sin permiso, SQLite, credenciales y derivados confidenciales.

**Aceptación:** diff revisado, control de frontera aprobado y relación de archivos autorizados por destino. Si la distribución de un requisito obligatorio sigue pendiente, publicar únicamente con autorización del conjunto y compatibilidad con las reglas. **Impacto:** confirmar destino dentro de T+15 y reservar hasta 5 minutos del cierre para revisión.

### SIM-004 · CI reproducible sin fuentes privadas

**Destino:** estándar §§13.11 y 14.7, TASK §§6 y 7. **Problema:** Spec quality falló cuando una spec referenció el PRD privado ausente en el checkout remoto.

> Ejecuta el gate íntegro de especificaciones en el ambiente autorizado con los RCTF presentes y el gate de checkout limpio sobre los mismos archivos que recibe CI. El remoto valida formato, trazabilidad estructural y referencias internas disponibles. El control local verifica huellas y referencias a originales privados. Documenta el alcance de cada ejecución. Queda prohibido subir un original privado para resolver el fallo del checkout.

**Aceptación:** pasa check_specs.py --checkout-sin-rctf en checkout equivalente a CI, pasa el control completo local y el informe indica el alcance de ambos. **Impacto:** 3 minutos antes de T+150. Iniciar el workflow en el bloque final cuando exista autorización de publicación.

### SIM-005 · Tres horas como límite operativo

**Destino:** TASK §4 y FORMAT §8. **Problema:** hubo trabajo posterior al corte de las 15:25 del ensayo.

> Registra hora de inicio, zona horaria y hora límite antes de escribir. A T+140 congela cambios de alcance y conserva el último candidato verificable. Dedica T+140 a T+165 a aceptación funcional y T+165 a T+180 a gates y entrega autorizada. A T+180 registra SHA, pruebas obtenidas y pendientes. Las correcciones posteriores pertenecen a otro registro y quedan fuera de la evaluación cronometrada.

**Aceptación:** marca del último candidato, resultados y estado de entrega con hora anterior o igual al límite. Un CI pendiente al vencer el plazo se registra como pendiente. **Impacto:** protege los últimos 40 minutos.

### SIM-006 · Integración documental y financiera desde el inicio

**Destino:** TASK §§3 y 6, INTERFACE §6. **Problema:** la validación integrada tardía dejó que las sugerencias documentales llegaran al modo financiero y ocultó el acoplamiento de los procesos web y API.

> En cuanto haya un PDF utilizable, abre la interfaz desde su URL y prueba una consulta documental con cita, una financiera incompleta y, si hay dos operandos verificables, una comparación con Decimal. Confirma modo, solicitud a la API, respuesta y apertura de la página física. Repite el smoke tras tocar selector de flujo, proveedor, proxy o visor. Registra los comandos de arranque y parada independientes de web y API.

**Aceptación:** antes de T+45 quedan registrados catálogo, ambos flujos y un PNG abierto. Si faltan datos de una comparación completa, registrarla pendiente y repetirla antes de T+100. **Impacto:** reserva 10 minutos de T+15 a T+45 y repite en aceptación.

### Hallazgo nuevo · Respaldo semántico y alcance de preguntas abiertas

**Destino:** PRD RF-10 y §9, TASK T-09/T-13 e INTERFACE §4.2. **Problema:** un PNG accesible y una cita pertinente coexistieron con un folio en la respuesta, una lista sin alcance y una referencia contable con texto genérico.

> Para una muestra mixta con oráculos cotejados contra los originales, registra por separado accesibilidad de cada cita, presencia textual y respaldo semántico de cada afirmación. Comprueba archivo, página física, contexto y asociación de encabezados, filas, columnas, moneda y periodo según corresponda. Coteja cada elemento de las listas, excluye pies y folios y evita contaminación entre columnas. Identifica expresamente las selecciones parciales sobre preguntas abiertas. Descarta los fragmentos sin respaldo y comunica el alcance restante o abstente. Un visor funcional y una coincidencia de texto solo acreditan sus respectivos controles.

**Aceptación:** una definición, una explicación con varios elementos, una consulta sin respaldo, dos comparaciones con resultados de distinta clase y una aclaración financiera. Cada afirmación tiene respaldo localizado o se declara la abstención. Se rechaza el caso si una cifra corresponde a otra fila, un pie se incorpora a la respuesta o falta contexto para una cita. **Impacto:** preparar oráculos en T+45 a T+100 y dedicar hasta 20 minutos a cotejo en T+140 a T+165.

### Hallazgo posterior · Robustez lingüística de la consulta documental

**Aplica a** PRD RF-03, RF-10 y §9, y TASK T-09/T-13. La pregunta corta de liquidez recuperaba tres políticas. Su paráfrasis con entidad explícita y un pedido de documento y página se abstenía porque la búsqueda exigía palabras de presentación.

> Separa el tema y la entidad de las restricciones de contenido y de las instrucciones sobre cómo presentar la respuesta. Descarta de la recuperación únicamente instrucciones de presentación reconocibles, como indicar el documento y la página de cada elemento. Conserva los periodos, entidades, monedas y demás condiciones que limitan el contenido. Las paráfrasis equivalentes, con las instrucciones antes, después o coordinadas con la pregunta, deben conservar las afirmaciones respaldadas y las citas que las demuestran. Si una restricción carece de respaldo, declara la limitación o abstente. No reduzcas los controles de evidencia para aprobar una paráfrasis.

**Aceptación.** Probar una pregunta breve y al menos tres formulaciones equivalentes que cambien el orden de las instrucciones. Cotejar los mismos elementos, la entidad y la página física. Repetir una variante con un periodo inexistente y comprobar que se abstiene. Verificar también que los casos financieros de moneda y comparabilidad conservan sus resultados. **Impacto.** Incluye 5 minutos del bloque de aceptación T+140–165, dentro del tiempo ya reservado para la muestra.

### Hallazgo posterior · Generalización de intención operativa

**Aplica a** PRD RF-03, RF-07, RF-08, RF-09 y §9, y TASK T-05/T-07/T-13. En la batería P01–P08, formulaciones naturales de porcentaje, diferencia entre tasas y comparación monetaria llegaron al flujo documental. Dos preguntas documentales no separaron el alcance de la fuente y el marco de su encabezado de los pedidos de presentación.

> Determina la intención por la operación solicitada y sus argumentos aunque el indicador, la entidad, la unidad o el intervalo aparezcan antes de la pregunta. Separa operación, indicador, entidad, periodos, moneda, escala y formato. Reconoce la diferencia entre variación relativa y diferencia entre tasas en puntos porcentuales. Las restricciones incompatibles requieren aclaración o abstención antes de devolver un cálculo. Para consultas documentales, valida emisor, tema y encabezado dentro del contexto original y conserva la cita de cada afirmación. Indica selección parcial si el modo extractivo no acredita exhaustividad.

**Aceptación.** En el entorno de la prueba, usa preguntas naturales definidas contra el corpus real. Incluye definición con emisor, lista contextualizada, variación relativa, diferencia en puntos porcentuales, comparación monetaria y abstenciones por futuro, periodo y stock. Para cada categoría prueba dos paráfrasis con distinto orden. Registra ruta, intención normalizada, evidencia, resultado, unidad y tiempo individual y máximo. Comprueba que cambios de moneda, entidad o periodo sigan siendo vinculantes. **Impacto.** Incluye las variantes dentro de la muestra de aceptación T+140–165 y usa los tiempos medidos para recortar trabajo opcional.

## Plan operativo de 180 minutos

La reutilización de código e índice depende de las reglas de Coder y de si el estado corresponde a los archivos autorizados. El catálogo real constituye una entrega distinta del ensayo.

| Reloj | Trabajo prioritario | Condición de salida |
|---|---|---|
| T+00–15 | Reloj, aislamiento, identidad del corpus, permisos, destino y servicios. Comprobar proveedor si existe autorización previa. | Entorno identificado y modo declarado. Ante falta de acceso o autorización, activar local. |
| T+15–45 | P0 con 1–2 PDF o estado compatible. Smoke web, API, recuperación, respuesta, cita y original. Probar los dos flujos. | Cita abierta y cotejada. Financiera incompleta pide periodos. Comparación completa si existen operandos. |
| T+45–100 | Ampliar ingesta incremental si hace falta. Ejercitar Decimal y abstención por base incompatible. Elegir oráculos contra originales. | Dos operandos comprobados, una abstención justificada y muestra definida. |
| T+100–140 | Corregir solo fallos de alto impacto y repetir smoke. Preparar candidato y checkout limpio. | Congelación de cambios de alcance a T+140. |
| T+140–165 | Aceptar la muestra en navegador, contrastar afirmaciones y páginas. Ejecutar regresiones. | Evidencia por caso, métricas separadas y riesgos. Descartar cambios con regresión crítica. |
| T+165–180 | Integridad, frontera, CI según destino, aprobación y publicación autorizada. | SHA publicado o preparado, CI y hora. Detener el trabajo al límite. |

## Decisión técnica por aprobar sobre inferencia desde backend

**Propuesta:** verificar autorización y acceso al inicio, con salida local inmediata si falta cualquiera. SPEC-002-AC-06 sigue **NOT RUN**. El criterio AC-06 del PRD corresponde a BM25.

| Capacidad del PRD | Evidencia local y dependencia |
|---|---|
| RF-01 a RF-05 y RF-12 | Catálogo, ingesta, FTS/BM25, lectura de originales/tabla y APIs se demuestran sin inferencia. |
| RF-06, RF-08 a RF-11 | Visor PNG, Decimal, comparabilidad, respuesta extractiva, citas y web operan localmente. Interpretar imágenes o gráficas exige un VLM autorizado y validación separada. |
| RF-07 y PRD AC-21 | Herramientas tipadas, recorrido y límites pueden verificarse con el doble. Un ciclo real del protocolo del proveedor y la planificación flexible requieren inferencia autorizada para acreditarse. Pruebas con mocks son evidencia de contrato local. |
| Explicaciones abiertas | El extractivo cita pasajes y listas comprobables y acota el alcance o se abstiene. Síntesis no literal, descomposición flexible y cobertura de formulaciones nuevas requieren validación separada. La inferencia por sí sola no garantiza fidelidad. |

1. **Preflight desde FastAPI.** Confirmar autorización del propietario. Dentro del runtime de la aplicación, suministrar la credencial del backend por el mecanismo aprobado y verificar TLS, identidad y permisos para el modelo autorizado. Ejecutar un ciclo con documento y pregunta ficticios. Comprobar llamada estructurada, validación de argumentos, ejecución de una sola herramienta de prueba de lectura y respuesta final con fuente ficticia. Registrar tiempo, modo, código y resultado saneado. Las credenciales de los asistentes del IDE quedan en su runtime.
2. **Datos autorizados.** Usar solo datos ficticios en la comprobación inicial. La autorización debe identificar proveedor, modelo, destino, vigencia, retención y categorías habilitadas. Las preguntas reales, fragmentos, tablas, metadatos identificables, imágenes y PDF completos requieren autorización específica antes del envío. Limitar contenido real autorizado al mínimo necesario y preservar procedencia en local. Excluir secretos e instrucciones privadas de payloads y registros.
3. **Presupuesto propuesto.** Una solicitud simultánea de preflight. Máximo dos llamadas y dos intentos totales de red por ciclo, sin reintentos implícitos, con 4 s por llamada y 12 s de deadline de backend. Como punto inicial, 1.500 tokens de entrada y 256 de salida por llamada. Antes del uso real, el propietario fija techo total de gasto y cuota. Aplicar los límites de herramientas y registrar latencia y consumo sin capturar contenido privado.
4. **Salida operativa.** Si faltan autorización, acceso, modelo, cuota o contrato compatible al terminar el preflight, verificar P0 extractivo y SPEC-002 con doble determinista. Registrar NOT RUN cuando no hubo prueba autorizada y FAIL cuando el intento autorizado no completó el ciclo. En modo local declarar cobertura dirigida, límites ante preguntas abiertas y ausencia de inferencia o inspección multimodal real.
