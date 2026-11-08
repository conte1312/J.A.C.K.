from __future__ import annotations

from app.ai.base_provider import BaseAiProvider
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.groq import GroqProvider
from app.ai.providers.nvidia import NvidiaNemotronProvider
from app.ai.providers.openrouter import OpenRouterProvider
from app.ai.providers.ollama import OllamaProvider

# Ordine predefinito di priorità dei provider per il routing intelligente.
# L'utente può modificarlo tramite l'AI Hub o le impostazioni.
DEFAULT_PROVIDER_ORDER = ("google", "groq", "openrouter", "ollama", "nvidia")


class ProviderRegistry:
    """Registro dei provider AI disponibili.

    Mappatura id provider -> classe adapter. I provider vengono istanziati
    singolarmente e possono essere abilitati/disabilitati dall'utente.
    """

    def __init__(self) -> None:
        self._providers: dict[str, type[BaseAiProvider]] = {
            "nvidia": NvidiaNemotronProvider,
            "google": GeminiProvider,
            "groq": GroqProvider,
            "openrouter": OpenRouterProvider,
            "ollama": OllamaProvider,
        }
        self._instances: dict[str, BaseAiProvider] = {}

    def get_provider_class(self, provider_id: str) -> type[BaseAiProvider] | None:
        return self._providers.get(provider_id)

    def get_provider(
        self, provider_id: str
    ) -> BaseAiProvider | None:
        if provider_id not in self._providers:
            return None
        if provider_id not in self._instances:
            provider_class = self._providers[provider_id]
            self._instances[provider_id] = provider_class()
        return self._instances[provider_id]

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())

    def is_registered(self, provider_id: str) -> bool:
        return provider_id in self._providers


registry = ProviderRegistry()
