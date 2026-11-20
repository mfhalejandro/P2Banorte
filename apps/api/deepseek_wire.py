"""Transporte HTTP de DeepSeek y validación del protocolo de herramientas."""
import asyncio
import json
import sqlite3
from dataclasses import dataclass
from typing import Annotated, Literal

import httpx
from pydantic import BaseModel, Field, ValidationError

from .agent import ProviderUnavailable
from .deepseek_config import INPUT_PRICE, OUTPUT_PRICE


class Function(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    arguments: str = Field(max_length=4096)


class ProposedCall(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    type: Literal["function"]
    function: Function


class Message(BaseModel):
    role: Literal["assistant"]
    content: str | None = Field(default=None, max_length=8192)
    tool_calls: list[ProposedCall] = Field(default_factory=list, max_length=24)


class Choice(BaseModel):
    message: Message
    finish_reason: Literal["stop", "tool_calls"]


TokenCount = Annotated[int, Field(strict=True, ge=0, le=2_000_000)]


class Usage(BaseModel):
    prompt_tokens: TokenCount
    completion_tokens: TokenCount


class Completion(BaseModel):
    choices: list[Choice] = Field(min_length=1, max_length=1)
    usage: Usage


@dataclass
class UsageTotals:
    prompt: int = 0
    output: int = 0
    calls: int = 0
    reserved_unconfirmed: int = 0

    @property
    def nano(self):
        return self.prompt * INPUT_PRICE + self.output * OUTPUT_PRICE


class DeepSeekHTTP:
    def __init__(self, settings, ledger, client):
        self.settings = settings
        self.ledger = ledger
        self.client = client

    async def ask(self, messages, tools, totals, *, final_only=False):
        settings = self.settings
        payload = {
            "model": settings.model,
            "messages": messages,
            "thinking": {"type": "disabled"},
            "max_tokens": settings.max_output_tokens,
            "response_format": {"type": "json_object"},
            "stream": False,
        }
        if tools:
            payload.update(tools=tools, tool_choice="none" if final_only else "auto")
        # Cota conservadora por bytes UTF-8 más sobrecarga del protocolo. La
        # contabilidad definitiva usa los tokens que devuelve el proveedor.
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        upper = len(encoded) + 512
        if upper > settings.max_input_tokens or totals.prompt + upper > settings.max_input_tokens * settings.max_calls:
            raise ProviderUnavailable("El contexto de DeepSeek alcanzó el límite de entrada.")
        if totals.calls >= settings.max_calls:
            raise ProviderUnavailable("Se agotaron las llamadas autorizadas a DeepSeek.")
        reserved = upper * INPUT_PRICE + settings.max_output_tokens * OUTPUT_PRICE
        try:
            self.ledger.reserve(reserved)
        except sqlite3.Error:
            raise ProviderUnavailable("El presupuesto de DeepSeek no está disponible.") from None
        totals.reserved_unconfirmed += reserved
        totals.calls += 1
        try:
            async with asyncio.timeout(settings.call_timeout):
                async with self.client.stream(
                    "POST", settings.base_url + "/chat/completions", content=encoded,
                    headers={"Authorization": "Bearer " + settings.api_key.get_secret_value(),
                             "Content-Type": "application/json", "Accept": "application/json"},
                ) as response:
                    status = response.status_code
                    if status != 200:
                        reason = {401: "autenticación rechazada", 402: "saldo insuficiente",
                                  403: "acceso rechazado", 429: "cuota o frecuencia agotada"}.get(status, "error HTTP")
                        raise ProviderUnavailable(f"DeepSeek: {reason} ({status}).")
                    data = bytearray()
                    async for chunk in response.aiter_bytes():
                        data.extend(chunk)
                        if len(data) > 262144:
                            raise ProviderUnavailable("DeepSeek devolvió una respuesta demasiado grande.")
            completion = Completion.model_validate_json(data)
        except (TimeoutError, httpx.TimeoutException):
            raise ProviderUnavailable("DeepSeek agotó el plazo de la llamada.") from None
        except httpx.RequestError:
            raise ProviderUnavailable("No se pudo conectar con DeepSeek.") from None
        except ValidationError:
            raise ProviderUnavailable("DeepSeek devolvió un protocolo o una terminación inválidos.") from None
        usage = completion.usage
        actual = usage.prompt_tokens * INPUT_PRICE + usage.completion_tokens * OUTPUT_PRICE
        try:
            self.ledger.reconcile(reserved, actual)
        except sqlite3.Error:
            raise ProviderUnavailable("No se pudo conciliar el presupuesto de DeepSeek.") from None
        totals.reserved_unconfirmed -= reserved
        totals.prompt += usage.prompt_tokens
        totals.output += usage.completion_tokens
        if usage.prompt_tokens > settings.max_input_tokens or usage.completion_tokens > settings.max_output_tokens:
            raise ProviderUnavailable("DeepSeek excedió los límites de tokens de la solicitud.")
        choice = completion.choices[0]
        if bool(choice.message.tool_calls) != (choice.finish_reason == "tool_calls"):
            raise ProviderUnavailable("DeepSeek devolvió una secuencia de herramientas inválida.")
        return choice.message
