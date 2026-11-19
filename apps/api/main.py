import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path, Query, Response

from .agent import Agent, ChatRequest, ChatResponse, LocalExtractive, ProviderUnavailable
from .corpus import Corpus
from .financial_agent import FinancialAgent


def create_app(corpus=None, provider=None, financial_provider=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.corpus = corpus or Corpus.configured()
        mode = os.getenv("LLM_PROVIDER", "extractive")
        if financial_provider is not None or (provider is None and mode == "financial-local"):
            app.state.agent = FinancialAgent(app.state.corpus, provider=financial_provider)
        else:
            app.state.agent = Agent(app.state.corpus, provider or LocalExtractive())
        app.state.provider_available = (
            provider is not None or financial_provider is not None or mode in {"extractive", "financial-local"}
        )
        yield

    app = FastAPI(title="Consulta financiera documental", lifespan=lifespan)

    @app.get("/api/health")
    def health():
        docs = app.state.corpus.catalog()
        return {"status": "ok", "documents": len(docs), "provider_mode": app.state.agent.provider.mode}

    @app.get("/api/documents")
    def catalog():
        return app.state.corpus.catalog()

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(body: ChatRequest):
        question = body.message.strip()
        if not question:
            raise HTTPException(422, "Escribe una pregunta.")
        if not app.state.provider_available:
            raise HTTPException(503, "El proveedor configurado no está disponible en este entorno.")
        try:
            return await app.state.agent.answer(question)
        except (TimeoutError, ProviderUnavailable, ConnectionError, OSError) as exc:
            raise HTTPException(503, "No se pudo completar la consulta. Vuelve a intentarlo.") from exc
        except KeyError as exc:
            raise HTTPException(409, "El índice cambió. Repite la consulta.") from exc

    @app.get("/api/documents/{doc_id}/pages/{pdf_page}/image", response_class=Response)
    def image(doc_id: Annotated[str, Path(pattern=r"^[a-f0-9]{64}$")],
              pdf_page: Annotated[int, Path(ge=1)], dpi: Annotated[int, Query(ge=72, le=180)] = 125):
        try:
            body = app.state.corpus.render(doc_id, pdf_page, dpi)
        except KeyError as exc:
            raise HTTPException(404, "La página o su documento original ya no están disponibles.") from exc
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(422, "La página no se pudo visualizar.") from exc
        return Response(body, media_type="image/png", headers={"Cache-Control": "private, no-store"})

    return app


app = create_app()
