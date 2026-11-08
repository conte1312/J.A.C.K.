from __future__ import annotations

import json
import socket
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.ai.base_provider import (
    ProviderInfo,
    ProviderModel,
    ProviderRequestError,
    BaseAiProvider,
)

GROQ_API_BASE = "https://api.groq.com/openai/v1/chat/completions"

# Modelli disponibili nel piano gratuito di Groq (al 2026).
# Verificare periodicamente su https://groq.com/pricing.
GROQ_MODELS = (
    ProviderModel(
        id="llama-3.1-8b-instant",
        name="Llama 3.1 8B Instant",
        description="Modello Groq veloce per conversazioni (piano gratuito).",
        is_free=True,
        context_window=131072,
        max_output_tokens=4096,
    ),
    ProviderModel(
        id="llama-3.1-70b-versatile",
        name="Llama 3.1 70B Versatile",
        description="Modello Groq avanzato per ragionamento (piano gratuito con limiti).",
        is_free=True,
        context_window=131072,
        max_output_tokens=4096,
    ),
    ProviderModel(
        id="mixtral-8x7b-32768",
        name="Mixtral 8x7B",
        description="Modello Groq misto di esperti (piano gratuito).",
        is_free=True,
        context_window=32768,
        max_output_tokens=4096,
    ),
)


class GroqProvider(BaseAiProvider):
    """Adapter per GroqCloud (piano gratuito, API compatibile OpenAI)."""

    def __init__(self, *, timeout: float = 60.0, transport=None) -> None:
        self._timeout = timeout
        self._transport = transport or self._post_json

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            id="groq",
            name="GroqCloud",
            provider_type="online",
            base_url=GROQ_API_BASE,
            requires_credential=True,
            is_free_tier_available=True,
            models=GROQ_MODELS,
        )

    async def chat(
        self,
        *,
        credential_value: str | None,
        model_id: str,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.6,
    ) -> str:
        if not credential_value:
            raise ProviderRequestError(
                "provider_not_configured",
                "Configura una chiave API Groq nell'AI Hub prima di continuare.",
                409,
            )
        if not self.is_model_free(model_id):
            raise ProviderRequestError(
                "model_not_free",
                f"Il modello {model_id} non è disponibile nel piano gratuito di Groq.",
                409,
            )
        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        response = await self._transport(credential_value, payload)
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ProviderRequestError(
                "invalid_provider_response",
                "Groq ha restituito una risposta non leggibile.",
                502,
            ) from error
        if not isinstance(content, str) or not content.strip():
            raise ProviderRequestError(
                "empty_provider_response",
                "Groq ha restituito una risposta vuota.",
                502,
            )
        return content.strip()

    async def test_connection(
        self,
        *,
        credential_value: str | None,
        model_id: str,
    ) -> bool:
        if not credential_value:
            raise ProviderRequestError(
                "provider_not_configured",
                "Configura una chiave API Groq nell'AI Hub prima di continuare.",
                409,
            )
        await self._transport(
            credential_value,
            {
                "model": model_id,
                "messages": [{"role": "user", "content": "Reply with OK."}],
                "temperature": 0.6,
                "max_tokens": 4,
                "stream": False,
            },
        )
        return True

    def is_model_free(self, model_id: str) -> bool:
        return any(m.id == model_id and m.is_free for m in GROQ_MODELS)

    def get_available_models(self) -> list[ProviderModel]:
        return list(GROQ_MODELS)

    async def _post_json(
        self,
        credential_value: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        request = Request(
            GROQ_API_BASE,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {credential_value}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:
                decoded = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise _provider_error_for_status(error.code) from None
        except (TimeoutError, socket.timeout):
            raise ProviderRequestError(
                "provider_timeout",
                "Groq non ha risposto entro il tempo previsto.",
                504,
            ) from None
        except URLError:
            raise ProviderRequestError(
                "provider_unreachable",
                "Non è stato possibile raggiungere il servizio Groq.",
                502,
            ) from None
        except (UnicodeDecodeError, json.JSONDecodeError, OSError):
            raise ProviderRequestError(
                "provider_unavailable",
                "Il servizio Groq ha restituito una risposta non valida.",
                502,
            ) from None
        if not isinstance(decoded, dict):
            raise ProviderRequestError(
                "invalid_provider_response",
                "Groq ha restituito una risposta non leggibile.",
                502,
            )
        return decoded


def _provider_error_for_status(status_code: int) -> ProviderRequestError:
    if status_code in (401, 403):
        return ProviderRequestError(
            "provider_authentication_failed",
            "Groq non ha accettato la chiave API. Verifica la configurazione.",
            401,
        )
    if status_code == 429:
        return ProviderRequestError(
            "provider_rate_limited",
            "Groq ha applicato un limite temporaneo. Attendi e riprova.",
            429,
        )
    if status_code in (400, 404, 422):
        return ProviderRequestError(
            "provider_request_rejected",
            "Groq ha rifiutato la richiesta o il modello non è disponibile.",
            502,
        )
    if status_code >= 500:
        return ProviderRequestError(
            "provider_unavailable",
            "Il servizio Groq non è al momento disponibile.",
            502,
        )
    return ProviderRequestError(
        "provider_request_failed",
        "La richiesta a Groq non è stata completata.",
        502,
    )
