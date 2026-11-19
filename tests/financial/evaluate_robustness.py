"""Evaluación local de SPEC-002. Usa el índice de los 24 PDF y emite JSON Lines."""
import json
from contextlib import redirect_stdout
import sys
from time import perf_counter

from fastapi.testclient import TestClient

from apps.api.corpus import Corpus
from apps.api.financial_agent import FinancialAgent, LocalToolDouble
from apps.api.main import create_app

CASES = [
 ("R01","Compara utilidad neta de GFNorte entre 2T24 y 3T24"),
 ("R02","Calcula la variación porcentual de la utilidad neta de GFNorte entre 2T24 y 3T24"),
 ("R03","Compara utilidad neta de GFNorte entre 9M23 y 9M24"),
 ("R04","Compara utilidad neta de GFNorte entre 1T24 y 2T25"),
 ("R05","Compara ROE de GFNorte entre 3T24 y 2T25"),
 ("R06","Compara ROE de GFNorte entre 2T24 y 3T24"),
 ("R07","Compara utilidad neta de GFNorte entre 2T24 y 3T24 en dólares"),
 ("R08","Compara capitalización de mercado (millones de dólares) entre 1T24 y 2T24"),
 ("R09","Compara capitalización de mercado (millones de pesos) entre 1T24 y 2T24"),
 ("R10","Compara utilidad neta de GFNorte entre 3T24 y 9M24"),
 ("R11","Compara utilidad neta de GFNorte entre 3T24 y 3T25"),
 ("R12","Compara utilidad neta de GFNorte entre 3T24 y 4T29"),
 ("R13","¿En cuánto cambió la utilidad neta de GFNorte de 2T24 a 3T24?"),
 ("R14","Calcula la suma de activo total de GFNorte entre 1T24 y 2T24"),
]

class AuditAgent(FinancialAgent):
    def __init__(self, corpus):
        super().__init__(corpus)
        self.steps = []
        self.names = {doc["doc_id"]: doc["filename"] for doc in corpus.catalog()}

    def execute(self, intent, trace, call):
        event = {"tool": call.name}
        self.steps.append(event)
        try:
            super().execute(intent, trace, call)
        except Exception as exc:
            event["error"] = str(exc)
            raise
        if call.name == "search_corpus":
            label = call.arguments["period"]
            event.update(
                period=label,
                candidates=[[self.names[ref.doc_id], ref.pdf_page] for ref in trace.searched[label]],
            )
        elif call.name == "read_source":
            ref = call.arguments["ref"]
            label = call.arguments["period"]
            values = [
                item for item in trace.observed.values()
                if item.period.label == label and item.citation.doc_id == ref["doc_id"]
                and item.citation.pdf_page == ref["pdf_page"]
            ]
            warnings = getattr(trace, "basis_warnings", {})
            reason, _ = warnings.get(label, (trace.rejected.get(label), None))
            event.update(
                period=label,
                source=[self.names[ref["doc_id"]], ref["pdf_page"]],
                values=[[item.original, item.unit.label, item.basis, item.note] for item in values],
                reason=None if values else reason,
            )


def main():
    selected = set(sys.argv[1:])
    if selected - {ident for ident, _ in CASES}:
        raise SystemExit("Hay identificadores de caso desconocidos.")
    corpus = Corpus.configured()
    if len(corpus.catalog()) != 24:
        raise SystemExit("La evaluación requiere el índice de los 24 PDF del ensayo.")
    app = create_app(corpus, financial_provider=LocalToolDouble())
    with TestClient(app) as client:
        for ident, question in CASES:
            if selected and ident not in selected:
                continue
            agent = AuditAgent(corpus)
            app.state.agent = agent
            start = perf_counter()
            with redirect_stdout(sys.stderr):
                response = client.post("/api/chat", json={"message": question})
            seconds = perf_counter() - start
            value = response.json()
            citations = []
            for cite in value.get("citations", []):
                url = f'/api/documents/{cite["doc_id"]}/pages/{cite["pdf_page"]}/image'
                image = client.get(url)
                png = image.status_code == 200 and image.content.startswith(bytes([137]) + b"PNG")
                citations.append([cite["filename"], cite["pdf_page"], cite["snippet"], png])
            record = {
                "case": ident,
                "question": question,
                "code": response.status_code,
                "status": value.get("status"),
                "answer": value.get("answer", value.get("detail")),
                "seconds": round(seconds, 3),
                "citations": citations,
                "steps": agent.steps,
            }
            print(json.dumps(record, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
