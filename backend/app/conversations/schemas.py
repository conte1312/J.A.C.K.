from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConversationRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class ConversationMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    conversation_id: str
    role: ConversationRole
    content: str
    created_at: datetime
    is_demo: bool = False
    provider_label: str | None = None


class ConversationWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=160)
    provider_id: str | None = Field(default=None, max_length=80)
    model_id: str | None = Field(default=None, max_length=160)
    metadata: dict[str, Any] | None = Field(default=None, max_length=2000)


class ConversationRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    provider_id: str | None
    model_id: str | None
    metadata: dict[str, Any]
    message_count: int = 0


class ConversationMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    conversation_id: str
    role: ConversationRole
    content: str
    created_at: datetime
    is_demo: bool = False
    provider_label: str | None = None


class ConversationListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    provider_id: str | None
    model_id: str | None
    message_count: int = 0


class ConversationMessageWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: ConversationRole
    content: str = Field(min_length=1, max_length=20_000)
    is_demo: bool = False
    provider_label: str | None = Field(default=None, max_length=120)


class ConversationRename(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=160)


class ConversationContextRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation: ConversationRead
    messages: list[ConversationMessage]
