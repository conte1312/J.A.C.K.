from __future__ import annotations

import json
import socket
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.ai.catalog import NVIDIA_CHAT_COMPLETIONS_URL
from app.ai.credentials import ProviderCredential


class ProviderRequestError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class NvidiaNemotronProvider:
    def __init__(self, *, timeout: float = 35.0, transport=None) -> None:
        self._timeout = timeout
        self._transport = transport or self._post_json

    def chat(
        self,
        *,
        credential: ProviderCredential,
        model_id: str,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
    ) -> str:
        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": 0.6,
            "max_tokens": max_tokens,
            "stream": False,
        }
        response = self._transport(credential, payload)
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ProviderRequestError(
                "invalid_provider_response",
                "NVIDIA ha restituito una risposta non leggibile.",
                502,
            ) from error
        if not isinstance(content, str) or not content.strip():
            raise ProviderRequestError(
                "empty_provider_response",
                "NVIDIA ha restituito una risposta vuota.",
                502,
            )
        return content.strip()

    def _post_json(
        self,
        credential: ProviderCredential,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        request = Request(
            NVIDIA_CHAT_COMPLETIONS_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {credential.value}",
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
                "NVIDIA non ha risposto entro il tempo previsto.",
                504,
            ) from None
        except URLError:
            raise ProviderRequestError(
                "provider_unreachable",
                "Non è stato possibile raggiungere il servizio NVIDIA.",
                502,
            ) from None
        except (UnicodeDecodeError, json.JSONDecodeError, OSError):
            raise ProviderRequestError(
                "provider_unavailable",
                "Il servizio NVIDIA ha restituito una risposta non valida.",
                502,
            ) from None
        if not isinstance(decoded, dict):
            raise ProviderRequestError(
                "invalid_provider_response",
                "NVIDIA ha restituito una risposta non leggibile.",
                502,
            )
        return decoded


def _provider_error_for_status(status_code: int) -> ProviderRequestError:
    if status_code in (401, 403):
        return ProviderRequestError(
            "provider_authentication_failed",
            "NVIDIA non ha accettato la chiave API. Verifica la configurazione.",
            401,
        )
    if status_code == 429:
        return ProviderRequestError(
            "provider_rate_limited",
            "NVIDIA ha applicato un limite temporaneo. Attendi e riprova.",
            429,
        )
    if status_code in (400, 404, 422):
        return ProviderRequestError(
            "provider_request_rejected",
            "NVIDIA ha rifiutato la richiesta o il modello non è disponibile.",
            502,
        )
    if status_code >= 500:
        return ProviderRequestError(
            "provider_unavailable",
            "Il servizio NVIDIA non è al momento disponibile.",
            502,
        )
    return ProviderRequestError(
        "provider_request_failed",
        "La richiesta a NVIDIA non è stata completata.",
        502,
    )
