from __future__ import annotations

import os
from dataclasses import dataclass

try:
    import keyring  # type: ignore
except ImportError:  # pragma: no cover - keyring opzionale
    keyring = None


@dataclass(frozen=True)
class ProviderCredential:
    value: str
    source: str  # "keychain" | "environment"


class CredentialManager:
    """Gestisce le API key per ogni provider AI.

    Le credenziali sono custodite nel macOS Keychain quando disponibile,
    altrimenti falliscono su variabile d'ambiente. Nessuna credenziale
    viene mai esposta nei log o restituita al frontend.
    """

    KEYCHAIN_SERVICE = "J.A.C.K."

    def __init__(self, keyring_module=None) -> None:
        self._keyring_module = keyring_module

    def _keyring(self):
        if self._keyring_module is not None:
            return self._keyring_module
        return keyring

    def get_credential(self, provider_id: str) -> ProviderCredential | None:
        """Restituisce la credenziale per un provider specifico.

        Cerca prima nel Keychain (account: J.A.C.K.<provider_id>_API_KEY),
        poi nella variabile d'ambiente (<PROVIDER_ID>_API_KEY).
        """
        keyring = self._keyring()
        if keyring is not None:
            try:
                account = f"{self.KEYCHAIN_SERVICE}.{provider_id.upper()}_API_KEY"
                value = keyring.get_password(self.KEYCHAIN_SERVICE, account)
            except Exception:
                value = None
            if isinstance(value, str) and value.strip():
                return ProviderCredential(value=value.strip(), source="keychain")

        env_var = f"{provider_id.upper()}_API_KEY"
        value = os.getenv(env_var, "").strip()
        if value:
            return ProviderCredential(value=value, source="environment")
        return None

    def save_credential(self, provider_id: str, value: str) -> None:
        """Salva la credenziale per un provider nel Keychain macOS."""
        keyring = self._keyring()
        if keyring is None:
            raise RuntimeError(
                "Il Keychain macOS non è disponibile. Configura "
                f"{provider_id.upper()}_API_KEY nel file .env locale."
            )
        try:
            account = f"{self.KEYCHAIN_SERVICE}.{provider_id.upper()}_API_KEY"
            keyring.set_password(self.KEYCHAIN_SERVICE, account, value)
        except Exception as error:
            raise RuntimeError(
                f"Non è stato possibile salvare la chiave per {provider_id}."
            ) from error

    def delete_credential(self, provider_id: str) -> None:
        """Rimuove la credenziale per un provider dal Keychain."""
        keyring = self._keyring()
        if keyring is None:
            return
        try:
            account = f"{self.KEYCHAIN_SERVICE}.{provider_id.upper()}_API_KEY"
            keyring.delete_password(self.KEYCHAIN_SERVICE, account)
        except Exception as error:
            if error.__class__.__name__ != "PasswordDeleteError":
                raise RuntimeError(
                    f"Non è stato possibile rimuovere la chiave per {provider_id}."
                ) from error
