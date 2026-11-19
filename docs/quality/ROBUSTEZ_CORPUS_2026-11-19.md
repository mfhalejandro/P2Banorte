# Robustez de SPEC-002 sobre 24 PDF de ensayo

**2026-11-19 · Codex · Evaluación local y dirigida.** Línea base `4792514`, segunda medición con las correcciones de esta evaluación. Se reutilizó el índice existente sin reingesta. Sus 24 SHA-256 coincidieron con los originales, con 5.899 páginas declaradas y 34.662 fragmentos. Los 14 casos son una muestra dirigida y no estiman la cobertura general del corpus ni de Coder. AC-06 sigue en NOT RUN, pendiente de autorización independiente. La evaluación usa el doble determinista y el render local de páginas.

## Método y criterios

Se cotejaron por separado encabezados, filas, cifras y notas con `pdftotext -layout` y se calcularon los oráculos con aritmética decimal. La ejecución usó `POST /api/chat` mediante el cliente de pruebas de FastAPI. Se capturaron páginas candidatas y lecturas para distinguir recuperación, extracción, comparabilidad, cálculo y orquestación. Para cada cita emitida se pidió el PNG a la ruta del visor, se comprobó la página del archivo correcto y se contrastó qué afirmación podía respaldar.

Un acierto completo exige cifra, unidad y respaldo correctos, o abstención con la causa específica del caso y su nota cuando exista. Un rechazo seguro con causa incompleta se registra como parcial. Las cifras parciales de una abstención se cotejan por separado y no cuentan como resultados de cálculo. Las páginas son físicas y empiezan en 1.

| Métrica | Base `4792514` | Después de las correcciones |
|---|---:|---:|
| Aciertos completos | 5/14 | 11/14 |
| Resultados numéricos exactos, con unidad y dos operandos respaldados | 3/8 | 6/8 |
| Abstenciones en casos que las exigían | 5/6 | 6/6 |
| Abstenciones con la causa y respaldo esperados | 2/6 | 5/6 |
| Respuestas de cálculo improcedentes | 1 | 0 |
| Citas emitidas cuyo PNG se pudo abrir | 14/14 | 21/21 |
| Mediana / máximo de latencia del POST | 3,80 s / 4,59 s | 4,72 s / 6,93 s |
| Errores HTTP | 0/14 | 0/14 |

El tiempo cubre el POST, antes de abrir el PNG. Las ejecuciones se hicieron en el entorno compartido, sin una prueba de carga controlada. La línea base de R07 abrió las páginas correctas para **pesos** y aun así falló la pregunta en **dólares**.

## Registro por caso

Las preguntas exactas y los pasos del agente son reproducibles con el [ejecutor local](../../tests/financial/evaluate_robustness.py).

| Caso y pregunta | Esperado y fuentes comprobadas | Base | Obtenido y citas | Diagnóstico |
|---|---|---|---|---|
| **R01** Utilidad neta de GFNorte, 2T24 → 3T24 | **+220 millones de pesos**. 14.018 → 14.238 en `3T24.pdf`, p. 5. | +220 con ambas citas. | **Exacto**. Ambas columnas de `3T24.pdf`, p. 5, y 2/2 PNG válidos. | Cálculo y procedencia correctos. |
| **R02** Variación porcentual del mismo par | **+1,57 %** sobre base 14.018. `3T24.pdf`, p. 5. | +1,57 % con ambas citas. | **Exacto**. `3T24.pdf`, p. 5, 2/2 citas válidas. | Fórmula y redondeo correctos. |
| **R03** Utilidad neta acumulada, 9M23 → 9M24 | **+3.089 millones de pesos**. 39.375 → 42.464 en `3T24.pdf`, p. 5. | +3.089 con ambas citas. | **Exacto**. `3T24.pdf`, p. 5, 2/2 citas válidas. | Selección de columnas acumuladas de igual duración. |
| **R04** Utilidad neta entre documentos, 1T24 → 2T25 | **Abstención bajo la regla de unidad común**. 14.208 en `1T24_A.pdf`, p. 5, y `2T24.pdf`, p. 5; 14.618 en `2T25_vc_.pdf`, p. 5. Ambas leyendas dicen pesos sin un código de moneda común demostrado por la herramienta. | Mostró ambas cifras exactas, pero afirmó incompatibilidad sin distinguir que faltaba acreditar la moneda común. | **Abstención justificada**. 14.208 y 14.618 exactos, `2T24.pdf`, p. 5, y `2T25_vc_.pdf`, p. 5. 2/2 citas válidas. | Comparabilidad conservadora entre tablas. Causa corregida. |
| **R05** ROE entre documentos, 3T24 → 2T25 | **+0,7 pp**. 22,9 % en `3T24.pdf`, p. 6, y `4T24_1.pdf`, p. 6. 23,6 % en `2T25_vc_.pdf`, p. 6. Las notas de ROE documentan la misma definición. | Abstención sin cifras ni citas. | **Exacto**. `4T24_1.pdf`, p. 6, y `2T25_vc_.pdf`, p. 6. 2/2 citas válidas. | Recuperación de la sección y extracción de la fila ROE con nota. |
| **R06** ROE, 2T24 → 3T24, tabla compleja | **−0,4 pp**. 23,3 % → 22,9 % en `3T24.pdf`, p. 6, fila ROE con nota 2. | Abstención sin cifras ni citas. | **Exacto**. `3T24.pdf`, p. 6, 2/2 citas válidas. | El parser delimita la sección e identifica la nota sin confundir el bloque contable contiguo. |
| **R07** Utilidad neta 2T24 → 3T24 solicitada en dólares | **Abstención**. `3T24.pdf`, p. 5, respalda 14.018 y 14.238 en pesos, sin conversión acreditada para los operandos. | **Resultado improcedente** de 220 millones de pesos. Las citas respaldaban pesos. | **Abstención justificada** por moneda solicitada. Cifras en pesos exactas, 2/2 citas válidas a `3T24.pdf`, p. 5. | El planificador descartaba el sufijo de moneda. Corregido. |
| **R08** Capitalización de mercado en millones de dólares, 1T24 → 2T24 | **−8.461 millones de dólares**. 30.761 → 22.300 en `2T24.pdf`, p. 7. Base corroborada en `1T24_A.pdf`, p. 7. | Abstención, sin citas. | **Sin resultado numérico**. Rechazó la página base y quedó sin candidato para 2T24. 0 citas. | Recuperación y extracción. La página 7 de 2T24 no llegó a candidatos y la extracción junta renglones de monedas. |
| **R09** Capitalización de mercado en millones de pesos, 1T24 → 2T24 | **−101.624 millones de pesos**. 508.555 → 406.931 en `2T24.pdf`, p. 7. Base corroborada en `1T24_A.pdf`, p. 7. | Abstención, sin citas. | **Sin resultado numérico**. Sin columna inequívoca en la base y sin celda válida en el periodo consultado. 0 citas. | Recuperación y extracción. La lectura de 2T24 se desvía a p. 27. La tabla correcta fusiona etiquetas y valores de ambos renglones. |
| **R10** Utilidad neta 3T24 frente a 9M24 | **Abstención** por trimestre frente a acumulado. 14.238 y 42.464 en `3T24.pdf`, p. 5. | Abstención específica con ambas cifras y citas. | **Abstención justificada**. Ambos valores exactos, 2/2 citas válidas de `3T24.pdf`, p. 5. | Comparabilidad por tipo y duración correcta. |
| **R11** Utilidad neta, 3T24 → 3T25 | **Abstención con advertencia citada**. Original de 3T24 en `3T24.pdf`, p. 5. `3T25_vc.pdf`, pp. 3 y 5, advierte desconsolidación de Bineo y limita la comparabilidad. | Se abstuvo genéricamente por entidad o base. Solo citó 3T24. | **Abstención justificada**. 14.238 del periodo base en `4T24_1.pdf`, p. 5. Advertencia en `3T25_vc.pdf`, p. 5. 2/2 citas válidas. | La lectura perdía la nota al descartar el operando. Corregido. |
| **R12** Utilidad neta, 3T24 → 4T29 | **Abstención por periodo ausente**. 14.238 en `3T24.pdf`, p. 5, y `4T24_1.pdf`, p. 5. El índice no devuelve candidato para 4T29. | Abstención explícita y cita de 3T24. | **Abstención justificada**. 14.238 exacto, 1/1 cita válida en `4T24_1.pdf`, p. 5. | Recuperación con ausencia esperada. |
| **R13** «¿En cuánto cambió… de 2T24 a 3T24?» | **+220 millones de pesos**, `3T24.pdf`, p. 5, mismos operandos que R01. | Abstención sin evidencia. La búsqueda recibió parte de la frase como nombre de métrica. | **Exacto**. Ambos operandos correctos y 2/2 citas válidas a `3T24.pdf`, p. 5. | Orquestación del enunciado natural corregida. |
| **R14** Sumar activo total de 1T24 y 2T24 | **Abstención por saldos de cierre no aditivos**. 2.395.399 y 2.435.012 millones de pesos en `2T24.pdf`, p. 6. | Abstención genérica sin cifras ni citas. | **Abstención segura, causa incompleta**. La lectura no establece celdas válidas. 0 citas. | Recuperación de la base y extracción del bloque de saldos. El límite de aditividad nunca llegó a ejecutarse. |

## Prioridad para el cierre

- **P0 corregido — moneda solicitada (R07).** Se valida la moneda pedida antes de devolver el cálculo. La prueba cubre rechazo en dólares y respuesta respaldada en MXN. La regresión también verifica que un candidato descartado por reexpresión no añada una advertencia a otro diagnóstico.
- **P1 corregidos — ROE con notas (R05/R06), Bineo (R11) y enunciado natural (R13).** La recuperación prioriza la sección con encabezados del indicador. Se exige la definición cuando una fila lleva marcador numérico y se rechazan definiciones diferentes. Un candidato de base no acreditada conserva su nota para la abstención pertinente. R13 separa la métrica del enunciado y del periodo.
- **Pendiente de mayor valor — R08/R09.** Recuperar el encabezado multiperiodo y separar los renglones fusionados de dólares y pesos en la página 7. Cualquier corrección debe validar las dos variantes y abstenerse si las celdas siguen siendo ambiguas.
- **Pendiente — R14.** Conservar el rechazo seguro y distinguir saldo no aditivo de fallo de lectura. Para comparaciones monetarias entre documentos como R04, acreditar explícitamente la escala y la misma moneda en ambas tablas antes de habilitar el cálculo.
- **Cálculo.** En las seis respuestas numéricas finales, diferencias, variación, puntos porcentuales y unidades coincidieron con los oráculos. Los fallos pendientes se producen antes de la calculadora.

## Reproducción

Desde la raíz, con el índice existente de los 24 PDF:

```bash
export RAG_DATA_DIR="$PWD/docs/requirements/data"
export RAG_STATE_DIR=/ruta/al/estado-de-24-pdf
PYTHONPATH=. .venv/bin/python -B tests/financial/evaluate_robustness.py > /tmp/p2-robustez.jsonl
.venv/bin/python -B -m pytest -p no:cacheprovider -q tests/financial tests/p0 tests/harness
```

Se pueden indicar casos al final del primer comando, por ejemplo `R05 R07 R11`. Las trazas detalladas incluyen únicamente datos del ensayo local, con páginas candidatas, lecturas, citas y resultado HTTP.
