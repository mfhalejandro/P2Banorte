---
name: rag-corpus-retrieval
description: Desarrollar o diagnosticar descubrimiento de PDF, ingesta, FTS5, ranking, tablas y localización de páginas.
---

# rag-corpus-retrieval

Usa [el contrato técnico](../../../docs/requirements/technology_stack.md) §§3–4 y el PRD RF-01 a RF-06. Para una cita desplazada, sigue el mismo `doc_id` y `pdf_page` desde búsqueda hasta render. La API usa páginas desde 1. Convierte a índice desde 0 solo en el adaptador PDF.

Descubre los PDF desde la raíz de datos autorizada y rechaza enlaces que escapen. Distingue archivo físico de contenido único por SHA-256. Reingiere solo contenido cambiado y aísla errores por documento. Mantén SQLite, cachés y derivados fuera del corpus. Tablas solo bajo demanda por página, con encabezados, notas y caché por hash, página y versión del parser.

Verifica FTS5 con acentos, símbolos y consultas vacías, MATCH parametrizado y BM25 ascendente. En comparativas recupera cada periodo antes del límite global. Mide antes de habilitar ONNX/RRF en el presupuesto de 2 CPU/4 GB. Cierra con los casos aplicables T-01 a T-06 o T-16 y una referencia verificable a página. Para discrepancias de cifra deriva al skill financiero.
