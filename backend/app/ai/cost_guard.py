from __future__ import annotations

from app.ai.base_provider import BaseAiProvider, ProviderRequestError


class CostGuard:
    """Protezione assoluta contro costi involontari.

    Garantisce che:
    - Nessuna richiesta venga inviata a modelli a pagamento.
    - Nessun fallback verso piani premium.
    - Nessun acquisto di crediti.
    - Nessun upgrade automatico.
    - Se un provider non offre più accesso gratuito, venga disabilitato.
    """

    def __init__(self, registry) -> None:
        self._registry = registry

    def assert_model_is_free(
        self, provider_id: str, model_id: str
    ) -> None:
        """Solleva un'eccezione se il modello non è gratuito."""
        provider = self._registry.get_provider(provider_id)
        if provider is None:
            raise ProviderRequestError(
                "unknown_provider",
                f"Il provider '{provider_id}' non è registrato.",
                404,
            )
        if not provider.is_model_free(model_id):
            raise ProviderRequestError(
                "model_not_free",
                f"Il modello '{model_id}' non è disponibile nel piano gratuito del provider '{provider_id}'. "
                "J.A.C.K. non invia richieste a modelli a pagamento.",
                409,
            )

    def assert_provider_is_free_tier(
        self, provider_id: str
    ) -> None:
        """Solleva un'eccezione se il provider non ha un piano gratuito."""
        provider = self._registry.get_provider(provider_id)
        if provider is None:
            raise ProviderRequestError(
                "unknown_provider",
                f"Il provider '{provider_id}' non è registrato.",
                404,
            )
        if not provider.info.is_free_tier_available:
            raise ProviderRequestError(
                "provider_not_free",
                f"Il provider '{provider_id}' non offre un piano gratuito. "
                "J.A.C.K. non può utilizzarlo senza rischio di costi.",
                409,
            )

    def get_free_providers(self) -> list[str]:
        """Restituisce l'elenco dei provider con piano gratuito disponibile."""
        free = []
        for provider_id in self._registry.list_providers():
            provider = self._registry.get_provider(provider_id)
            if provider is not None and provider.info.is_free_tier_available:
                free.append(provider_id)
        return free
