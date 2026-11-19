"""Agente extractivo local. El proveedor elige entre evidencias leídas por las herramientas."""
import asyncio
import re
from typing import Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field

from .corpus import Citation, Corpus, SearchRequest, asks_definition, terms


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1200)


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    warnings: list[str]
    tools_used: list[str]
    request_id: str
    provider_mode: str
    status: Literal["answered", "abstained"]


class Provider(Protocol):
    mode: str

    async def select(self, question: str, evidence: list[Citation]) -> str | None: ...


class LocalExtractive:
    mode = "extractivo local"

    async def select(self, question, evidence):
        if not evidence:
            return None
        best = max(evidence, key=lambda item: sentence_score(question, passage(question, item.snippet)))
        score = sentence_score(question, passage(question, best.snippet))
        if asks_definition(question) and not score[1]:
            return None
        return best.evidence_id


class ProviderUnavailable(Exception):
    pass


def sentence_score(question, sentence):
    wanted = set(terms(question))
    overlap = len(wanted.intersection(terms(sentence)))
    definition = asks_definition(question) and any(
        cue in sentence.casefold() for cue in ("se refiere", "se define", "consiste", "es la posibilidad", " es el ", " es una ", " es un ", " es la ")
    )
    return overlap, definition


def passage(question, body):
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿])", body)
    return max(sentences, key=lambda part: sentence_score(question, part))


class Agent:
    def __init__(self, corpus: Corpus, provider: Provider, max_calls=6, timeout=12):
        self.corpus = corpus
        self.provider = provider
        self.max_calls = max_calls
        self.timeout = timeout

    async def answer(self, question):
        used = []

        async def call(name, tool, arg):
            if len(used) >= self.max_calls:
                raise ProviderUnavailable("Se alcanzó el límite de herramientas")
            used.append(name)
            return await asyncio.to_thread(tool, arg)

        def result(status, answer, citations):
            return ChatResponse(status=status, answer=answer, citations=citations, warnings=[],
                                tools_used=used, request_id=uuid4().hex, provider_mode=self.provider.mode)

        async with asyncio.timeout(self.timeout):
            found = await call("search_corpus", self.corpus.search_corpus, SearchRequest(query=question))
            observed = {}
            for ref in found[:4]:
                citation = await call("read_source", self.corpus.read_source, ref)
                observed[citation.evidence_id] = citation
            if observed:
                selected = await self.provider.select(question, list(observed.values()))
                if selected in observed:
                    citation = observed[selected]
                    return result("answered", passage(question, citation.snippet), [citation])
            return result("abstained", "No encontré evidencia suficiente en los documentos indexados para responder a esta pregunta.", [])
