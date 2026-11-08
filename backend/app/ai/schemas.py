from __future__ import annotations

from typing import Any, Literal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class ProviderType(str, Enum):
    online = "online"
    local = "local"


class ProviderModelSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    is_free: bool
    context_window: int | None = None
    max_output_tokens: int | None = None


class ProviderInfoSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    provider_type: ProviderType
    base_url: str | None
    requires_credential: bool
    is_free_tier_available: bool
    models: list[ProviderModelSchema]


class ProviderStateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    available: bool = False
    last_error: str | None = None
    quota_exhausted: bool = False


class RouterConfigSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_order: list[str]
    enabled_providers: list[str]
    max_retries_per_provider: int
    failover_enabled: bool


class CredentialInput(BaseModel):
    api_key: SecretStr = Field(min_length=8, max_length=1000)


class ModelSelectionInput(BaseModel):
    model_id: str = Field(min_length=1, max_length=160)


class ModelEnabledInput(BaseModel):
    enabled: bool


class ConnectionTestInput(BaseModel):
    model_id: str = Field(min_length=1, max_length=160)


class ProviderCredentialInput(BaseModel):
    provider_id: str = Field(min_length=1, max_length=80)
    api_key: SecretStr = Field(min_length=8, max_length=1000)


class ProviderOrderInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_order: list[str] = Field(min_length=1)


class ProviderEnableInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: str = Field(min_length=1, max_length=80)
    enabled: bool


class ChatTurnInput(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=32000)


class ChatInput(BaseModel):
    model_id: str | None = Field(default=None, max_length=160)
    messages: list[ChatTurnInput] = Field(min_length=1, max_length=50)
