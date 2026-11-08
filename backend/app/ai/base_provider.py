from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderModel:
    """Definizione di un modello supportato da un provider."""

    id: str
    name: str
    description: str
    is_free: bool
    context_window: int | None = None
    max_output_tokens: int | None = None


@dataclass(frozen=True)
class ProviderInfo:
    """Informazioni statiche su un provider AI."""

    id: str
    name: str
    provider_type: str  # "online" | "local"
    base_url: str | None
    requires_credential: bool
    is_free_tier_available: bool
    models: tuple[ProviderModel, ...]


class ProviderRequestError(Exception):
    """Errore sollevato da un provider AI durante una richiesta."""

    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class BaseAiProvider(abc.ABC):
    """Interfaccia comune per tutti i provider AI di J.A.C.K.

    Ogni adapter provider implementa questa classe astratta per garantire
    che il routing e il servizio AI possano trattare i provider in modo
    uniforme, indipendentemente dal servizio cloud sottostante.
    """

    @property
    @abc.abstractmethod
    def info(self) -> ProviderInfo:
        """Informazioni statiche del provider."""

    @abc.abstractmethod
    async def chat(
        self,
        *,
        credential_value: str | None,
        model_id: str,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.6,
    ) -> str:
        """Invia una richiesta di completamento chat e restituisce il testo della risposta."""

    @abc.abstractmethod
    async def test_connection(
        self,
        *,
        credential_value: str | None,
        model_id: str,
    ) -> bool:
        """Verifica che il provider risponda e che il modello sia disponibile."""

    @abc.abstractmethod
    def is_model_free(self, model_id: str) -> bool:
        """Restituisce True se il modello è nel piano gratuito del provider."""

    @abc.abstractmethod
    def get_available_models(self) -> list[ProviderModel]:
        """Restituisce l'elenco dei modelli supportati dal provider."""
