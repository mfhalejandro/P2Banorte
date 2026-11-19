"""Agente extractivo local. El proveedor elige entre evidencias leídas por las herramientas."""
import asyncio
import re
from functools import partial
from typing import Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field

from .corpus import Citation, Corpus, SearchRequest, DEFINITION_LEAD, definition_source, definition_topic, documentary_query, explanation_terms, terms


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
        if definition_topic(question) and not sentence_score(question, passage(question, best.snippet))[0]:
            return None
        return best.evidence_id


class ProviderUnavailable(Exception):
    pass


def sentence_score(question, sentence):
    topic = definition_topic(question)
    wanted = terms(topic or question)
    overlap = len(set(wanted).intersection(terms(sentence)))
    if not topic or not wanted or overlap != len(wanted):
        return False, overlap
    heading, colon, body = sentence.partition(": ")
    under_heading = bool(colon and terms(heading) == wanted and DEFINITION_LEAD.match(body))
    inline = re.split(r"\s+(?:se refiere |se define |consiste |es (?:el|la|un|una) )", sentence, maxsplit=1, flags=re.I)
    return under_heading or (len(inline) == 2 and terms(inline[0]) == wanted), overlap


def passage(question, body):
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿])", body)
    return max(sentences, key=lambda part: sentence_score(question, part))


def list_items(snippet):
    return {
        re.sub(r"^(?:el|la|los|las)\s+", "", item.strip().casefold())
        for item in snippet.split("•")[1:]
    }


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

        no_evidence = "No encontré evidencia suficiente en los documentos indexados para responder a esta pregunta."
        query = documentary_query(question)
        if not query:
            return result("abstained", no_evidence, [])
        async with asyncio.timeout(self.timeout):
            found = await call("search_corpus", self.corpus.search_corpus, SearchRequest(query=query))
            observed = {}
            topic = definition_topic(query)
            explain = explanation_terms(query) if not topic else set()
            read_source = (
                partial(self.corpus.read_source, topic=topic, explain=explain, source=definition_source(query) if topic else None)
                if topic or explain else self.corpus.read_source
            )
            for ref in found[:4]:
                citation = await call("read_source", read_source, ref)
                if citation.snippet:
                    observed[citation.evidence_id] = citation
            if observed:
                selected = await self.provider.select(query, list(observed.values()))
                if selected in observed:
                    citation = observed[selected]
                    if explain:
                        primary = citation.snippet.partition(":")[0]
                        items = list_items(citation.snippet)
                        extra = next((item for item in observed.values()
                                      if item.snippet.partition(":")[0].casefold() != primary.casefold()
                                      and list_items(item.snippet) - items), None)
                        citations = [citation, extra] if extra else [citation]
                        answer = "En los fragmentos verificados se encontró la siguiente información. La selección es parcial. "
                        return result("answered", answer + " ".join(item.snippet for item in citations), citations)
                    return result("answered", passage(query, citation.snippet), [citation])
            return result("abstained", no_evidence, [])
