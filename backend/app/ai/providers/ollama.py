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

OLLAMA_API_BASE = "http://localhost:11434/api/chat"

# Ollama è un provider locale: i modelli dipendono da ciò che l'utente ha scaricato.
# Non vengono elencati modelli predefiniti perché Ollama non li fornisce automaticamente.
OLLAMA_MODELS: tuple[ProviderModel, ...] = ()


class OllamaProvider(BaseAiProvider):
    """Adapter per Ollama (provider locale, alternativa senza costi)."""

    def __init__(self, *, timeout: float = 120.0, transport=None) -> None:
        self._timeout = timeout
        self._transport = transport or self._post_json

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            id="ollama",
            name="Ollama",
            provider_type="local",
            base_url="http://localhost:11434",
            requires_credential=False,
            is_free_tier_available=True,
            models=OLLAMA_MODELS,
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
        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "num_predict": max_tokens,
            "stream": False,
        }
        response = await self._transport(payload)
        try:
            content = response["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ProviderRequestError(
                "invalid_provider_response",
                "Ollama ha restituito una risposta non leggibile.",
                502,
            ) from error
        if not isinstance(content, str) or not content.strip():
            raise ProviderRequestError(
                "empty_provider_response",
                "Ollama ha restituito una risposta vuota.",
                502,
            )
        return content.strip()

    async def test_connection(
        self,
        *,
        credential_value: str | None,
        model_id: str,
    ) -> bool:
        await self._transport(
            {
                "model": model_id,
                "messages": [{"role": "user", "content": "Reply with OK."}],
                "temperature": 0.6,
                "num_predict": 4,
                "stream": False,
            },
        )
        return True

    def is_model_free(self, model_id: str) -> bool:
        # Ollama è locale: tutti i modelli installati sono gratuiti.
        return True

    def get_available_models(self) -> list[ProviderModel]:
        # Ollama non fornisce un elenco predefinito; i modelli vengono scoperti dinamicamente.
        return []

    async def _post_json(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        request = Request(
            OLLAMA_API_BASE,
            data=json.dumps(payload).encode("utf-8"),
            headers={
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
                "Ollama non ha risposto entro il tempo previsto.",
                504,
            ) from None
        except URLError:
            raise ProviderRequestError(
                "provider_unreachable",
                "Non è stato possibile raggiungere Ollama locale. Assicurati che sia in esecuzione.",
                502,
            ) from None
        except (UnicodeDecodeError, json.JSONDecodeError, OSError):
            raise ProviderRequestError(
                "provider_unavailable",
                "Ollama ha restituito una risposta non valida.",
                502,
            ) from None
        if not isinstance(decoded, dict):
            raise ProviderRequestError(
                "invalid_provider_response",
                "Ollama ha restituito una risposta non leggibile.",
                502,
            )
        return decoded


def _provider_error_for_status(status_code: int) -> ProviderRequestError:
    if status_code in (401, 403):
        return ProviderRequestError(
            "provider_authentication_failed",
            "Ollama ha rifiutato la richiesta. Verifica la configurazione locale.",
            401,
        )
    if status_code == 429:
        return ProviderRequestError(
            "provider_rate_limited",
            "Ollama ha applicato un limite temporaneo. Attendi e riprova.",
            429,
        )
    if status_code in (400, 404, 422):
        return ProviderRequestError(
            "provider_request_rejected",
            "Ollama ha rifiutato la richiesta o il modello non è disponibile.",
            502,
        )
    if status_code >= 500:
        return ProviderRequestError(
            "provider_unavailable",
            "Il servizio Ollama non è al momento disponibile.",
            502,
        )
    return ProviderRequestError(
        "provider_request_failed",
        "La richiesta a Ollama non è stata completata.",
        502,
    )
