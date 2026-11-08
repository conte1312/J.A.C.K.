from __future__ import annotations

import os
from dataclasses import dataclass


KEYCHAIN_SERVICE = "J.A.C.K."
KEYCHAIN_ACCOUNT = "NVIDIA_API_KEY"


class CredentialStoreError(Exception):
    """Credential operation failed; messages never contain credential values."""


class EnvironmentCredentialError(CredentialStoreError):
    pass


@dataclass(frozen=True)
class ProviderCredential:
    value: str
    source: str


class CredentialStore:
    def __init__(self, keyring_module=None) -> None:
        self._keyring_module = keyring_module

    def _keyring(self):
        if self._keyring_module is not None:
            return self._keyring_module
        try:
            import keyring
        except ImportError:
            return None
        return keyring

    def get(self) -> ProviderCredential | None:
        keyring = self._keyring()
        if keyring is not None:
            try:
                value = keyring.get_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)
            except Exception:
                value = None
            if isinstance(value, str) and value.strip():
                return ProviderCredential(value=value.strip(), source="keychain")

        value = os.getenv("NVIDIA_API_KEY", "").strip()
        if value:
            return ProviderCredential(value=value, source="environment")
        return None

    def save(self, value: str) -> None:
        keyring = self._keyring()
        if keyring is None:
            raise CredentialStoreError(
                "Il Keychain macOS non è disponibile. Configura NVIDIA_API_KEY nel file .env locale."
            )
        try:
            keyring.set_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT, value)
        except Exception as error:
            raise CredentialStoreError(
                "Non è stato possibile salvare la chiave nel Keychain macOS."
            ) from error

    def delete(self) -> None:
        credential = self.get()
        if credential is not None and credential.source == "environment":
            raise EnvironmentCredentialError(
                "La chiave arriva da NVIDIA_API_KEY. Rimuovila dal file .env o dall'ambiente del backend."
            )

        keyring = self._keyring()
        if keyring is None:
            return
        try:
            keyring.delete_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)
        except Exception as error:
            # Removing an absent Keychain item is an idempotent operation.
            if error.__class__.__name__ != "PasswordDeleteError":
                raise CredentialStoreError(
                    "Non è stato possibile rimuovere la chiave dal Keychain macOS."
                ) from error
