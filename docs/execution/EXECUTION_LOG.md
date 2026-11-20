# Bitácora de ejecución

## 2026-11-19 · Implementación del arnés

Fuente: plan aceptado y confirmación humana de la entrega de 8 Markdown y 24 PDF. Responsable de ejecución: agente Codex. El solicitante autorizó implementar el arnés. La aprobación funcional del PRD sigue pendiente.

- Preflight de solo lectura: 32 archivos, 1 subdirectorio, huella idéntica a la confirmada, indicador de montaje de solo lectura activo y cero rutas escribibles. El sandbox ordinario rechazó la creación de un archivo raíz con EROFS. En el contexto autorizado se comprobó nuevamente la protección y se creó, leyó y retiró un archivo temporal en la raíz, exit 0.
- Desarrollo aislado con Python 3.12.3 y Git 2.43.0. `python3 -B -m unittest discover -s tests/harness -v`: 8 pruebas pasaron, exit 0, 1.466 s en la primera ejecución. Cada prueba Git usa un repositorio desechable. El validador local de skill-creator aceptó los diez skills (exit 0).
- Recorrido de mantenimiento: ante una cita desplazada, AGENTS dirige a responsive-frontend para verificar respuesta, enlace, petición y página. Si la respuesta ya trae el número incorrecto, rag-corpus-retrieval verifica la conversión de página. La evidencia esperada es T-09/AC-16 con el mismo par documento y página. Recorrido documental; la UI está pendiente.
- Recorrido financiero: financial-agent-evidence exige verificar ambos tipos de periodo, entidad, unidad y fuentes. Un trimestre contra un acumulado produce rechazo de la operación y abstención documentada en T-07/T-08. Recorrido documental; la calculadora está pendiente.
- Recorrido Git: release-governance conduce al manifiesto, a las capas de Git y al responsable humano. Un ZIP en el índice bloquea la entrega incluso si falta del árbol. El gate no modifica el índice.

Las pruebas funcionales del RAG, UI, integraciones externas y despliegues están en NOT RUN.

### 2026-11-19T19:59:19+01:00 · Verificación desde la raíz del proyecto

Se instalaron 26 archivos. La comprobación local resolvió los 44 enlaces Markdown y encontró las diez entradas de skill.

| Comando | Contexto | Resultado |
|---|---|---|
| `python3 -B scripts/quality/check_requirements.py --preflight` | Escritura en raíz autorizada, requisitos en montaje de solo lectura | PASS integridad, aislamiento y escritura temporal en raíz, exit 0 |
| `python3 -B -m unittest discover -s tests/harness -q` | Raíz instalada, fixtures en directorios temporales | PASS, 8 pruebas en 1.406 s, exit 0 |
| `python3 -B scripts/security/check_publication.py` | Árbol, índice real, repositorio sin primer commit | FAIL esperado, exit 1. Único hallazgo: índice, `docs/requirements.zip` |
| `git status --short` | Inspección final | Archivos nuevos del arnés sin preparar. Persisten los dos cambios iniciales del índice. |

Cierre de etapa: VERIFIED para el arnés local. PREPARADO / NO PUBLICADO. Decisiones pendientes: aprobación funcional del PRD y resolución humana del ZIP antes de publicación.

## 2026-11-19 · Corrección de la estructura documental

El solicitante señaló la ausencia de ADR, specs, SDD, planes y sprints y ratificó el estándar canónico. Se materializan las rutas de §§2, 6.2–6.3, 7.9 y 13. ADR-001 registra la elección humana del formato portable. SDD-001 describe los controles implementados en 816e4ba. SPEC-001 abre un borrador para revisar AC-16/17/18. La corrección documental del arnés se acoge a §13.3; el producto conserva su gate antes de implementación.

El preflight del contexto autorizado comprobó aislamiento, huella y escritura temporal en la raíz (exit 0). Al comenzar, el árbol y el índice estaban limpios y el gate de publicación pasó. El registro histórico del hallazgo anterior del ZIP se conserva arriba.

2026-11-19T20:08:08+01:00 · Verificación local desde la raíz: `python3 -B scripts/quality/check_specs.py` pasó para SPEC-001 y se comprobó el rechazo de ID duplicado, estado divergente y criterio sin trazabilidad. Se resolvieron los 71 enlaces de los documentos modificados. `python3 -B -m unittest discover -s tests/harness -q` pasó 8 pruebas en 2.253 s. Integridad RCTF, control automático de publicación y `git diff --check` terminaron con exit 0. Workflow remoto y pruebas funcionales de aplicación: NOT RUN.

## 2026-11-19T20:16:47+01:00 · Inicio de preparación de aplicación V3

Codex recuperó main en 13c659c. El preflight en la raíz autorizada pasó integridad, aislamiento y prueba temporal de escritura. El solicitante ratificó la arquitectura V3. El PRD de la entrega confirmada (SHA-256 7c66a68dbd121430cffbf16c6b637b8e0e69cdf2cbd655bcec70e1eed19eff0b) y SPEC-001 v2 se presentan para decisión funcional. Se conservan los tres criterios de v1 y se añaden ingesta, recuperación y agente al alcance del primer recorrido. Plan y tareas en preparación, pruebas del producto NOT RUN.

CI: en la [ejecución de GitHub](https://github.com/mfhalejandro/P2Banorte/actions/runs/44595451678), el job specs 135812375814 terminó con exit 1 en la referencia al PRD. El mismo fallo se reprodujo desde git archive de ese SHA. La corrección del workflow y del verificador pasó en un checkout limpio sin originales, usando únicamente el inventario confirmado. Las pruebas negativas rechazaron un Markdown privado ausente del inventario, un enlace de arquitectura roto, la entrega local ausente y una entrega parcial en modo CI. La validación del checkout no representa una aprobación funcional ni una ejecución remota del cambio.

Verificación final en el repositorio: preflight, spec en modo local estricto, diff --check, frontera de publicación y 8 pruebas del arnés pasaron. En un clon limpio de 13c659c se aplicaron únicamente los tres archivos de la corrección CI: el comando del workflow pasó también con la spec original v1, sin copiar requisitos ni incorporar el trabajo P0. Aprobación de producto y ejecución remota del cambio pendientes al registrar esta evidencia.

## 2026-11-19 · Aprobación e inicio de construcción

El solicitante aprobó el PRD V3 de la entrega confirmada y SPEC-001 v2 con «Autorizo las do desiciones.». Autorizó expresamente publicar CI y código P0 verificado en main sin originales RCTF. La rama temporal superó [Spec quality](https://github.com/mfhalejandro/P2Banorte/actions/runs/44597404997) en 3765a15.

### Verificación técnica del corte P0 · 2026-11-19

Se probaron las superficies del plan con Python 3.12, SQLite FTS5, React 19, Vite 7 y Chromium local. El agente usó el modo extractivo local, con búsqueda y lectura reales. Inferencia generativa externa: NOT RUN por falta de proveedor autorizado. Los originales, sus imágenes, el índice, entornos de dependencias y logs crudos quedan fuera de Git.

| Evidencia | Comando o recorrido | Resultado |
|---|---|---|
| P0-01 | Ingesta con `python -m apps.api.corpus --limit 2` y repetición | 24 PDF descubiertos, 2 indexados. Segunda ejecución: 2 reutilizados, 0 nuevos, 0 fallidos. |
| P0-01/02/03 | `python -m pytest -q tests/p0 tests/harness` | 15 pruebas pasaron en 5.87 s, además de 5 subcasos. Un aviso de deprecación del cliente de pruebas de Starlette. |
| P0-03 | `npm run build` | TypeScript y compilación de assets de desarrollo verificados, exit 0. |
| P0-03/04 | `npm run smoke`, servidores y PDF ficticio en loopback | 6 pruebas pasaron en 12.5 s. Cita a la página 2 en 320, 375, 768, 1024 y 1440 px, foco restaurado, error de fuente, reintento y abstención. |
| P0-04 | Consulta real «¿Qué es el riesgo de crédito?» en navegador a 375 px | Respuesta extractiva sobre incumplimiento de obligaciones de pago; la cita abrió la página 7 del mismo documento. Se cotejó el texto con pdftotext ejecutado sobre esa página del original y se comprobó la decodificación del PNG. |

Los límites del primer corte y el procedimiento de reproducción están en el [README](../../README.md).

## 2026-11-19 · Reanudación y propuesta de SPEC-002

Responsable: Codex. `git status --short --branch` mostró main limpio al reanudar. HEAD y origin/main coincidían en `4620231`. [Spec quality en main](https://github.com/mfhalejandro/P2Banorte/actions/runs/44600670150) pasó en ese SHA. Los verificadores de integridad y especificación pasaron. El preflight de escritura se ejecutó con el aislamiento de los originales intacto.

La aprobación previa cubre PRD V3, SPEC-001 y publicación de CI/P0. La sesión carece de configuración de inferencia del backend. No se ejecutaron llamadas externas de inferencia. Se propone [SPEC-002 v1](../../specs/SPEC-002-comparacion-financiera.md) en IN_REVIEW y se añaden sus criterios a la trazabilidad. La implementación del corte y sus pruebas quedan en NOT RUN. Se conserva la evidencia previa del P0.

### 2026-11-19 · Preparación local de la revisión funcional

El solicitante autorizó preparación técnica local y pruebas sintéticas con doble. SPEC-002 v1 sigue en IN_REVIEW. Se detallaron procedencia, lectura de tablas, comparabilidad, fórmulas y abstención, y se separó la aceptación con doble del ciclo real sujeto a autorización. Los criterios del nuevo corte permanecen en NOT RUN.

La comprobación preparatoria con PyMuPDF generó y reabrió dos PDF ficticios con encabezados trimestrales y acumulados y una cifra repetida en una celda señuelo. Validó la extracción de la matriz y los oráculos Decimal de diferencia de 12.29 millones MXN, variación de 11.06 % y diferencia de tasas de 1.5 puntos porcentuales. El archivo de ensayo y los PDF quedaron en un directorio temporal. Las tres pruebas sintéticas de línea base del doble P0 pasaron con `.venv/bin/python -B -m pytest -p no:cacheprovider -q tests/p0/test_slice.py -k provider_limits` (exit 0, 4.02 s). Cubren referencia inventada, proveedor caído, tiempo y presupuesto de herramientas del P0. No hubo llamadas a servicios externos.

## 2026-11-19 · Implementación financiera local

El solicitante aprobó SPEC-002 v1 para AC-01 a AC-05 y difirió expresamente AC-06. El preflight sobre `2898871` comprobó árbol limpio, huella, aislamiento y escritura temporal en raíz. El gate de spec aprobada pasó antes de iniciar el código. [Plan](../../plans/implementation-spec-002-financiero.md) · [Sprint](SPRINTS.md)

- Se reutilizó el estado de P0 de dos documentos y se comprobó búsqueda, cita y PNG con el código nuevo, sin migrar el índice. La apertura de un índice existente se verifica también mientras otra conexión está escribiendo.
- El smoke a 375 px con el frontend existente devolvió 12.29 millones para un par ficticio válido, abrió las dos páginas originales y se abstuvo al comparar trimestre con acumulado.
- La evaluación sintética con dos CPU comprobó cobertura Recall@5 de 2/2 periodos, acierto numérico 2/2, acierto de cita 4/4 y abstención correcta 2/2. En 12 solicitudes al conjunto de oráculos la mediana fue 70.1 ms, el máximo 125.2 ms y el RSS del proceso 188416 KiB. Esta muestra es un ensayo sintético local.
- La ingesta de originales de ensayo se ejecutó en un estado separado con `python -m apps.api.corpus --limit N`. Se midieron 2 documentos en 6.53 s, 8 en 19.36 s (2 reutilizados) y 24 en 257.55 s (8 reutilizados, 206592 KiB de RSS máximo, 0 fallos). Los nombres y hashes se descubrieron en ejecución. Dos corpus sintéticos adicionales ejercitaron alias, fallo aislado e interrupción.
- Consulta real sobre utilidad neta de GFNorte, 2T24 a 3T24: 14,018 a 14,238 millones de pesos, diferencia de 220. Ambas citas apuntan a las columnas respectivas de la tabla de la página 5 del mismo PDF. Se cotejó con `pdftotext -layout` y PyMuPDF. En 3T24 a 3T25 la aplicación se abstuvo porque la entidad o base del candidato de 3T25 no quedó acreditada inequívocamente. Estas dos consultas no representan una evaluación general del corpus.
- AC-06 en NOT RUN, pendiente de autorización independiente. Todo el circuito financiero de esta entrega usa un doble local. Los índices de ensayo, los originales RCTF y los PDF ficticios generados permanecen fuera de los cambios.

Regresión final: `python -B -m pytest -p no:cacheprovider -q tests/financial tests/p0 tests/harness`, 31 pruebas y 5 subcasos pasaron en 11.68 s. Se registró un aviso de deprecación de Starlette en el cliente de pruebas. La demo conserva el frontend de P0.

En el árbol compartido pasaron el gate de especificación, la integridad RCTF, el control automático de publicación y `git diff --check`. La demo se inició en loopback (web 5194, API 8194) con los 24 PDF del ensayo. Chromium a 375 px verificó allí el resultado real de 220 y decodificó la imagen de la página 5 al abrir cada cita.

## 2026-11-19 · Robustez de SPEC-002

Codex reanudó en `47925143cef894b8f1d40e884d2d4b85799a594e`, con árbol e índice limpios y coincidencia de HEAD con origin/main. Pasaron integridad y gate de especificación. Se reutilizó el índice de ensayo: 24 SHA cotejados, 5.899 páginas declaradas y 34.662 fragmentos. Se midieron las mismas 14 preguntas antes y después, con evaluación y cotejo local. [Protocolo de evaluación y resultados](../quality/ROBUSTEZ_CORPUS_2026-11-19.md)

La medición intermedia pasó 36 pruebas, 5 subcasos y 1 aviso de deprecación de Starlette en 16,36 s con `.venv/bin/python -B -m pytest -p no:cacheprovider -q tests/financial tests/p0 tests/harness`. Aciertos completos 11/14 y 21/21 páginas citadas abrieron sus PNG. La rama de extracción local y el índice de P0 conservan su contrato. AC-06 quedó en NOT RUN.

## 2026-11-19 · Implementación del cierre sobre la base `9929cb2`

Codex confirmó el commit manual del solicitante `9929cb2e078e12393ded2bed3d2eae3f32100e1a` en HEAD, origin/main y la consulta de solo lectura a la rama remota. El árbol estaba limpio antes de aplicar el cierre. Pasaron los controles de integridad, aislamiento y especificación. Se reutilizó el índice de 24 PDF sin reingesta.

El ejecutor `tests/financial/evaluate_robustness.py` pasó 14/14 de la muestra. Se cotejaron R08 y R09 contra `2T24.pdf`, p. 7, con diferencias respectivas −8.461 millones de dólares y −101.624 millones de pesos. R14 se abstuvo por saldo no aditivo antes de usar herramientas. La comparación JSON confirmó que los otros 11 casos retienen código HTTP, estado, texto y citas. Se abrieron 25/25 PNG. Las 6 pruebas `npm run smoke` de P0 pasaron en 19,6 s sobre Chromium. [Informe de cierre](../quality/ROBUSTEZ_CORPUS_2026-11-19.md)

El cierre prepara únicamente cambios locales del arnés de pruebas, código y documentación. AC-06 queda NOT RUN. La frontera Git excluye los originales RCTF, el corpus, los índices y las credenciales.

Regresión final `.venv/bin/python -B -m pytest -p no:cacheprovider -q tests/financial tests/p0 tests/harness`: 41 pruebas y 5 subcasos pasaron en 13,12 s. Se observó el aviso preexistente de deprecación del cliente de pruebas de Starlette. Se verificaron cambios contra 9929cb2 y se preparó exclusivamente el cierre local para revisión.

## 2026-11-19 15:03 CDMX · Cierre definitivo de `5307d2b`

Codex confirmó el mismo SHA en HEAD, origin/main y `refs/heads/main` del remoto. Al reanudar, el árbol y el índice Git estaban limpios. Los 24 PDF coincidieron por SHA-256 con el manifiesto y el índice de 34.662 fragmentos. Los originales RCTF estaban en solo lectura y fuera de Git. Pasaron los controles de integridad, especificaciones y frontera de publicación.

| Evidencia | Verificación | Resultado |
|---|---|---|
| GitHub Actions, commit `5307d2b` | `Spec quality` sobre el checkout publicado | PASS · [ejecución 44613640612](https://github.com/mfhalejandro/P2Banorte/actions/runs/44613640612) |
| Local, checkout limpio de `5307d2b` | `python3 -B scripts/quality/check_specs.py --checkout-sin-rctf` | PASS · 2 especificaciones |
| Local, evaluación dirigida | `PYTHONPATH=. .venv/bin/python -B tests/financial/evaluate_robustness.py` con el índice existente | 14/14 casos completos, 8/8 cálculos, 6/6 abstenciones justificadas, 25/25 PNG. La comparación JSON confirmó el código HTTP, estado, texto y citas de los 14 casos del cierre anterior. Mediana POST 4,34 s, máximo 6,07 s. |
| Local, regresión Python | `.venv/bin/python -B -m pytest -p no:cacheprovider -q tests/financial tests/p0 tests/harness` | PASS · 41 pruebas, 5 subcasos, 18,24 s. Aviso de deprecación preexistente de Starlette. |
| Local, navegador P0 | `npm run smoke` en `apps/web` con Chromium preinstalado | PASS · 6 pruebas, 17,1 s. |
| Local, dependencias | `uv lock --check --offline --no-cache --python /usr/bin/python3` y `npm --prefix apps/web ls --depth=0` | PASS · lock Python coherente y dependencias web presentes. |

Se conservó el índice existente durante la verificación. Los resultados 5/14 y 11/14 se mantienen como mediciones históricas en el [informe](../quality/ROBUSTEZ_CORPUS_2026-11-19.md). El alcance de la confirmación es la muestra dirigida. SPEC-002-AC-06 permanece en NOT RUN. Las instrucciones de [instalación y ejecución](../../README.md) y de recuperación y evaluación están en los documentos existentes.

## 2026-11-19 15:31 CDMX · Recuperación y corrección posterior al cierre

La revisión local comenzó en `e7920a5` con HEAD y origin/main alineados y el árbol limpio. El lanzador anterior finalizaba ambos servicios cuando uno salía. El log confirma el cierre de Uvicorn con PID 3851035. Los dos puertos estaban libres al reanudar. API y Vite quedaron activos en 8194 y 5194 como unidades independientes de systemd de usuario. El reinicio de la API conservó el PID de Vite. [Arranque y parada](../../README.md#recuperar-la-demo-con-un-índice-existente)

En `financial-local`, `/api/chat` separa las peticiones financieras explícitas de la consulta documental de P0. Una solicitud de cálculo incompleta pide los operandos que faltan. Para una definición, P0 verifica que el texto corresponda al concepto solicitado y, si está bajo un encabezado de la página original, conserva su columna. Se reutilizó el SQLite existente. Su SHA-256 permaneció idéntico, con 24 PDF cotejados y 34.662 fragmentos.

| Control local | Resultado |
|---|---|
| `.venv/bin/python -B -m pytest -p no:cacheprovider -q tests/p0 tests/financial tests/harness` | PASS · 46 pruebas y 5 subcasos. Aviso preexistente de Starlette. |
| `npm run smoke` en `apps/web` | PASS · 6 pruebas de Chromium. |
| `PYTHONPATH=. .venv/bin/python -B tests/financial/evaluate_robustness.py` con el índice existente | PASS · 14/14 iguales a la línea base en estado HTTP, respuesta, citas y herramientas. 8 cálculos, 6 abstenciones y 25/25 PNG válidos. |
| Chromium contra 5194 y verificación de salud en 8194 | PASS · Biblioteca de 24 documentos. Riesgo de crédito y políticas de liquidez con evidencia de P0. Comparación GFNorte 2T24 a 3T24 de +220 millones de pesos con dos citas. Solicitud incompleta con aclaración y trimestre frente a acumulado con abstención. Seis citas abiertas en el visor. |

Las métricas del simulacro cerrado se conservan. AC-06 permanece NOT RUN. La corrección se verificó localmente.

## 2026-11-19 16:06 CDMX · Auditoría funcional previa a la prueba real

Codex reanudó en 7f37024 con HEAD y origin/main alineados, árbol e índice Git limpios. El preflight confirmó integridad, aislamiento y escritura fuera de los originales. Se mantuvieron la API y Vite independientes y se reutilizó el índice de los 24 PDF.

Se capturaron las seis respuestas antes de aplicar cambios. D02 y F02 quedaron PARTIAL y F01 FAIL. Tras corregir extracción, alcance, unidad y evidencia de perímetro, el ejecutor de aceptación local y Chromium pasaron los seis casos. Se verificaron 6/6 citas accesibles, 6/6 textuales y 6/6 semánticas de esa muestra. La regresión Python pasó 48 pruebas y 5 subcasos. El smoke aislado pasó 6 pruebas. El ejecutor de robustez reprodujo 14/14 y 25/25 PNG. R11 conserva la abstención con el párrafo de la advertencia.

La evidencia de hoy es posterior al cierre de las 15:25. Se conservan la arquitectura V3 y las métricas históricas. El propietario debe revisar la propuesta RCTF y la decisión sobre inferencia. SPEC-002-AC-06 sigue NOT RUN. [Informe, comandos y oráculos](../quality/AUDITORIA_FUNCIONAL_PRUEBA_REAL.md) · [Propuesta y plan](../quality/PROPUESTA_RCTF_PRUEBA_REAL.md)

## 2026-11-19 16:20 CDMX · Paráfrasis e instrucciones de presentación

Codex reanudó en 68d2783 con HEAD y origin/main alineados y los cambios locales e índice Git limpios. Los originales pasaron integridad y aislamiento. La consulta extensa de D02 se abstuvo antes de leer fuentes por un umbral de 8/10 términos que incluía formato.

Se normalizaron las cláusulas documentales de presentación, se preservó el umbral del 80 % y se conservaron los controles de tema, entidad, restricciones numéricas y encabezado. Se deduplicaron las viñetas idénticas de fuentes repetidas. La consulta larga y otras tres formulaciones mantienen las mismas tres políticas de la página física 152. La variante para 2035 se abstiene.

Pasaron 11/11 casos de aceptación en el servicio y en Chromium, con 10/10 páginas abiertas y citas comprobadas semánticamente. Python pasó 49 pruebas y 5 subcasos. El smoke pasó 6 pruebas. Los 14 casos financieros conservaron respuestas, citas y herramientas de la última auditoría y 25/25 PNG. La propuesta RCTF incorpora un criterio lingüístico reproducible. SPEC-002-AC-06 sigue NOT RUN. [Auditoría](../quality/AUDITORIA_FUNCIONAL_PRUEBA_REAL.md) · [Propuesta](../quality/PROPUESTA_RCTF_PRUEBA_REAL.md)

## 2026-11-19 · Generalización lingüística P01–P08

Reanudación en d747950 con HEAD y origin/main alineados y el índice Git limpio. Pasaron integridad RCTF y aislamiento. Se reutilizó el SQLite sin reingesta y se conservó su huella. Las ocho preguntas exactas pasaron en Chromium y se abrieron sus diez citas. La suite de 14 casos financieros volvió a pasar con 25 PNG. El negativo de entidad reveló que el flujo podía citar una nota de otro grupo al abstenerse. Se corrigió la atribución y el negativo ahora se abstiene por discrepancia de entidad sin citas. [Trazas y latencias](../quality/AUDITORIA_FUNCIONAL_PRUEBA_REAL.md#generalización-lingüística-p01p08-sobre-d747950)

## Integración DeepSeek · a partir de 2fab9ef

Codex verificó HEAD, origin/main, árbol limpio, originales, 24 PDF e índice confirmado. El entorno cargó .env con permisos 0600, excluido de Git. Se mantuvo la demo local y se levantó una unidad temporal en loopback con corpus generado por el backend. Se autorizó únicamente DeepSeek Flash con datos ficticios. La revisión automática rechazó la invocación que contenía la bandera de corpus real y no se ejecutó esa parte. El bloqueo se comprobó con transporte simulado y sin llamadas.

FastAPI completó tres baterías reales con 10/10, 8/10 y 10/10. La ejecución final confirmó tool calling, Decimal, citas y control de instrucciones del PDF. Los dos cierres inválidos de la segunda batería motivaron una recuperación parcial conservadora cuando ya existen fuentes verificadas. Se emplearon 117 llamadas, 188.985 tokens de entrada y 8.751 de salida, con USD 0,0671967 estimados como cota. Se detuvo solo la unidad de pago. [Resultados, controles y comandos](../quality/AUDITORIA_FUNCIONAL_PRUEBA_REAL.md#deepseek-real-sobre-un-corpus-sintético--a-partir-de-2fab9ef)


## 2026-11-19T18:24-06:00 CDMX · Preflight A/B y autorización pendiente

Codex comprobó 5df777b, integridad RCTF, 24 PDF, SQLite, 22 oráculos congelados y servicios de loopback. Pasaron las 12 pruebas de MockTransport. .env ya indicaba true para corpus real, con el proveedor inactivo, y se dejó intacto. El ledger original confirmó USD 0,0671967 acumulados. La salida queda pendiente de derechos, retención, autorización expresa y techo de gasto. NOT RUN para la nueva A/B. [Evidencia y solicitud](../quality/AUDITORIA_FUNCIONAL_PRUEBA_REAL.md#preflight-ab-g01g22-sobre-5df777b)

## 2026-11-19 18:33–18:36 CDMX · Evaluación A/B G01–G22

Codex reanudó en `e2f3abb`, alineado con origin/main y con árbol e índice limpios. Los cambios publicados desde la línea base de DeepSeek `5df777b` eran exclusivamente documentales. Pasaron los controles RCTF y de especificaciones. Coincidieron las huellas del corpus y del SQLite existente. El propietario autorizó una sola pasada G01–G22 con informes públicos y un techo acumulado de USD 1,00 en el ledger original.

Las dos unidades loopback con 2 CPU y 4 GiB ejecutaron `tests/financial/evaluate_deepseek.py independent` sobre los mismos oráculos. Local reprodujo 16/22. DeepSeek logró 7/22 y tuvo tres 503 de cierre inválido, diferenciados de los nueve FAIL de calidad. Se registraron 98 llamadas y USD 0,0633432 estimados, con USD 0,1305399 acumulados conciliados. Se detuvieron las dos unidades temporales. La demo permanente siguió en modo local. La configuración global se preservó, incluido el valor preexistente de `DEEPSEEK_ALLOW_REAL_DATA`, y se comprobó offline el bloqueo al declarar `false` explícitamente. [Resultados, cotejos y límites](../quality/AUDITORIA_FUNCIONAL_PRUEBA_REAL.md#evaluación-ab-g01g22)

## 2026-11-19 · Rescate híbrido experimental

Codex reanudó en `b0722dd`, con origin/main alineado, originales protegidos y SQLite reutilizado. El modo de rescate ejecuta V3 localmente, valida el plan JSON y conserva evidencias, cifras y abstenciones. Pasaron 81 pruebas Python, 5 subcasos, 6 Chromium y las regresiones 14/14, 11/11, 28/28 y B01–B10. En la regresión inicial, dos ejecutores P0 heredaron el proveedor real preexistente y enviaron solo fixtures. El ledger separado registró USD 0,0219033 estimados. Se fijó deliberadamente el proveedor extractivo en ambos ejecutores y se repitió con salida bloqueada.

El propietario autorizó una pasada G01–G22 con techo acumulado USD 0,18. Se obtuvieron 16/22 local y 21/22 híbrido. Hubo cuatro planes, coste estimado USD 0,0005019, ledger original en USD 0,1310418 y cero reservas. Las instancias temporales se detuvieron. J01–J20 quedó en 5/20 en las tres variantes locales, incluida la del doble. El híbrido permanece experimental. [Auditoría y límites](../quality/AUDITORIA_FUNCIONAL_PRUEBA_REAL.md#búsqueda-híbrida-experimental)

## 2026-11-20 · Sprint de generalización híbrida

Codex verificó `e912da2`, integridad RCTF, 24 PDF y SQLite existente. Implementó requisitos por apartado y comprobación de origen, fecha, entidad y divisa. La pasada exploratoria K, congelada antes de medir, obtuvo 7/12 local y 9/12 con el híbrido simulado. El último filtro de moneda generó un falso rechazo en tres pruebas conocidas. Se archivó la versión de K, se distinguió la entidad de la divisa y se confirmó el cierre en 97 pruebas Python, 5 subcasos, 6 Chromium, 14/14 financieros, 11/11 de aceptación, 28/28 ampliada y 10/10 en B01–B10. No se repitió K. La comparación externa queda NOT RUN y el ledger original permanece en USD 0,1310418. [Auditoría y evidencia](../quality/AUDITORIA_FUNCIONAL_PRUEBA_REAL.md#sprint-de-generalización-híbrida)

## 2026-11-20T21:57:10+01:00 · Reinicio local de la demo

Se reiniciaron p2banorte-api.service y p2banorte-web.service con systemctl --user restart. La API directa en 8194 y a través de Vite en 5194 informó estado ok, 24 documentos y modo financial-local. El frontend respondió HTTP 200.

## 2026-11-20T22:28:17+01:00 · Rescate local en la demo web

Codex verificó la salida bloqueada y activó hybrid-experimental con el planificador determinista en p2banorte-api.service. La web en 5194 comprobó D05, F05 y S06. En A/B, 13 PASS locales se conservaron y B obtuvo 20/20, 31/31 citas pertinentes, seis rescates completos y cero consumo externo. Pasaron 103 pruebas Python, 5 subcasos, 6 Chromium, 14/14 financieros, 11/11 de aceptación, 28/28 ampliada y 10/10 B. Los RCTF, PDF, SQLite y ledger original quedaron intactos. [Auditoría](../quality/AUDITORIA_FUNCIONAL_PRUEBA_REAL.md#rescate-determinista-local-en-la-aplicación-web)

## 2026-11-20T22:39:51+01:00 · Reinicio de la API de la demo

Se ejecutó `systemctl --user restart p2banorte-api.service` y se confirmó el cambio de PID. La API directa en 8194 y mediante Vite en 5194 informó estado ok, 24 documentos, planificador determinista y salida externa bloqueada. El frontend respondió HTTP 200. El modo y el alcance declarados en `.env` coincidían con los de la unidad, que conserva sus variables explícitas.

## 2026-11-20T23:22:56+01:00 · Diagnóstico y generalización del híbrido determinista

Codex reanudó en `2fa82a6` y conservó la edición de bitácora que ya estaba en el árbol. Ejecutó L por HTTP antes del cambio, cotejó los PDF y congeló M. Las instancias temporales usaron `uvicorn bench_app:app`, SQLite de solo lectura, dos CPU, 4 GiB y solo loopback. El candidato final dio 25/25 en L y 5/12 en M. Pasaron las regresiones publicadas en el informe, 108 pruebas Python y los 6 smoke de Chromium. La demo en 8194/5194 comprobó L02 y L15 con PNG originales. No se ejecutó DeepSeek. [Informe](../quality/AUDITORIA_FUNCIONAL_PRUEBA_REAL.md#generalización-del-híbrido-determinista--línea-base-2fa82a6)
