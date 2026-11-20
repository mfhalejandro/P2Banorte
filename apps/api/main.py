import os
import sqlite3
from contextlib import AsyncExitStack, asynccontextmanager
from tempfile import TemporaryDirectory
from typing import Annotated

import httpx
from fastapi import FastAPI, HTTPException, Path, Query, Response

from .agent import Agent, ChatRequest, ChatResponse, LocalExtractive, ProviderUnavailable
from .corpus import Corpus
from .deepseek_agent import DataNotAuthorized, DeepSeekAgent
from .deepseek_config import SpendLedger, runtime_env, settings_from_env
from .deepseek_fixture import HYBRID_QUESTIONS, synthetic_corpus
from .deepseek_wire import DeepSeekHTTP
from .financial_agent import FinancialAgent, requires_financial_tools
from .hybrid_agent import HybridAgent
from .hybrid_planner import DeterministicPlanner, HybridPlanner, planner_settings, question_hash, read_allowlist


async def configure_hybrid(app, stack, corpus, injected_planner, transport):
    scope = os.getenv("HYBRID_DEEPSEEK_SCOPE", "blocked")
    planner = injected_planner
    effective = "in-process" if planner is not None else "blocked"
    if planner is None and scope in {"synthetic", "authorized"}:
        try:
            if scope == "synthetic":
                allowed = frozenset(question_hash(q) for q in HYBRID_QUESTIONS.values())
            else:
                allowed = read_allowlist(os.getenv("HYBRID_DEEPSEEK_ALLOWLIST"))
            settings = planner_settings()
            if settings.api_key.get_secret_value():
                meter = SpendLedger(settings.budget_file, settings.budget_usd)
                client = await stack.enter_async_context(httpx.AsyncClient(
                    trust_env=False, follow_redirects=False, transport=transport,
                ))
                planner = HybridPlanner(DeepSeekHTTP(settings, meter, client), allowed)
                effective = scope
        except (OSError, ValueError, sqlite3.Error, ProviderUnavailable):
            pass  # El backend conserva el modo local aun con egress deshabilitado.
    if scope == "synthetic" and injected_planner is None:
        directory = stack.enter_context(TemporaryDirectory(prefix="p2-hybrid-fixture-"))
        corpus = synthetic_corpus(directory)
    app.state.corpus = corpus or Corpus.configured()
    app.state.hybrid_ready = isinstance(planner, HybridPlanner)
    local_planner = planner if planner is not None else DeterministicPlanner()
    app.state.agent = HybridAgent(Agent(app.state.corpus, LocalExtractive()), FinancialAgent(app.state.corpus), local_planner)
    app.state.external_data_scope = effective
    app.state.provider_available = True
    app.state.financial_enabled = False
    app.state.deepseek_enabled = False


def create_app(corpus=None, provider=None, financial_provider=None, *, deepseek_transport=None, hybrid_planner=None):
    @asynccontextmanager
    async def lifespan(app):
        injected = provider is not None or financial_provider is not None
        env = {} if injected else runtime_env()
        mode = env.get("LLM_PROVIDER", os.getenv("LLM_PROVIDER", "extractive"))
        async with AsyncExitStack() as stack:
            app.state.hybrid_enabled = mode == "hybrid-experimental" and not injected
            if app.state.hybrid_enabled:
                await configure_hybrid(app, stack, corpus, hybrid_planner, deepseek_transport)
            elif mode == "deepseek" and not injected:
                settings = settings_from_env(env)
                if settings.synthetic and settings.allow_real_data:
                    raise ProviderUnavailable("Los modos sintético y de corpus real son excluyentes.")
                if settings.synthetic:
                    corpus_dir = stack.enter_context(TemporaryDirectory(prefix="p2-deepseek-fixture-"))
                    app.state.corpus = synthetic_corpus(corpus_dir)
                else:
                    app.state.corpus = corpus or Corpus.configured()
                adapter = None
                if settings.api_key.get_secret_value() and (settings.synthetic or settings.allow_real_data):
                    try:
                        state_path = settings.budget_file.expanduser().resolve()
                        if state_path.is_relative_to(app.state.corpus.db.parent.resolve()):
                            raise ProviderUnavailable("El presupuesto debe estar separado del índice.")
                        meter = SpendLedger(settings.budget_file, settings.budget_usd)
                    except (OSError, sqlite3.Error, ProviderUnavailable):
                        meter = None
                    if meter:
                        client = await stack.enter_async_context(httpx.AsyncClient(
                            trust_env=False, follow_redirects=False, transport=deepseek_transport,
                        ))
                        adapter = DeepSeekHTTP(settings, meter, client)
                app.state.agent = DeepSeekAgent(app.state.corpus, adapter, settings, synthetic=settings.synthetic)
                app.state.financial_enabled = False
                app.state.deepseek_enabled = True
                app.state.deepseek_ready = adapter is not None
                app.state.external_data_scope = (
                    "synthetic" if settings.synthetic else "authorized" if settings.allow_real_data else "blocked"
                )
                app.state.provider_available = True  # El agente comunica credencial o política no disponible.
            else:
                app.state.corpus = corpus or Corpus.configured()
                app.state.documentary_agent = Agent(app.state.corpus, provider or LocalExtractive())
                app.state.financial_enabled = financial_provider is not None or (provider is None and mode == "financial-local")
                app.state.agent = (
                    FinancialAgent(app.state.corpus, provider=financial_provider)
                    if app.state.financial_enabled else app.state.documentary_agent
                )
                app.state.deepseek_enabled = False
                app.state.provider_available = injected or mode in {"extractive", "financial-local"}
            yield

    app = FastAPI(title="Consulta financiera documental", lifespan=lifespan)

    @app.get("/api/health")
    def health():
        docs = app.state.corpus.catalog()
        mode = app.state.agent.mode if app.state.hybrid_enabled else app.state.agent.provider.mode
        result = {"status": "ok", "documents": len(docs), "provider_mode": mode}
        if app.state.hybrid_enabled:
            result["external_data_scope"] = app.state.external_data_scope
            result["external_provider_ready"] = app.state.hybrid_ready
            result["planner"] = app.state.agent.planner_mode
        if app.state.deepseek_enabled:
            result["external_data_scope"] = app.state.external_data_scope
            result["external_provider_ready"] = app.state.deepseek_ready
        return result

    @app.get("/api/documents")
    def catalog():
        return app.state.corpus.catalog()

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(body: ChatRequest, response: Response):
        question = body.message.strip()
        if not question:
            raise HTTPException(422, "Escribe una pregunta.")
        if not app.state.provider_available:
            raise HTTPException(503, "El proveedor configurado no está disponible en este entorno.")
        agent = app.state.agent
        if app.state.financial_enabled and not requires_financial_tools(question):
            agent = app.state.documentary_agent
        metrics = {}
        try:
            if app.state.deepseek_enabled or app.state.hybrid_enabled:
                result = await agent.answer(question, metrics=metrics)
                response.headers.update(metrics)
                return result
            return await agent.answer(question)
        except DataNotAuthorized:
            raise HTTPException(403, "El envío a DeepSeek no está autorizado para esta consulta.") from None
        except ProviderUnavailable as exc:
            if app.state.deepseek_enabled:
                raise HTTPException(503, str(exc), headers=metrics) from None
            raise HTTPException(503, "No se pudo completar la consulta. Vuelve a intentarlo.") from exc
        except (TimeoutError, ConnectionError, OSError) as exc:
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
