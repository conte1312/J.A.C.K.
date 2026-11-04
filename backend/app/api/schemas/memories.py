from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MemoryCategory(str, Enum):
    identity = "identity"
    work = "work"
    projects = "projects"
    people = "people"
    technical = "technical"
    preferences = "preferences"
    events = "events"
    other = "other"


class MemorySourceType(str, Enum):
    saved = "saved"
    retrieved = "retrieved"
    inference = "inference"


class MemoryVerification(str, Enum):
    verified = "verified"
    to_verify = "to_verify"
    inferred = "inferred"


LEGACY_CATEGORY_MAP = {
    "personale": MemoryCategory.identity.value,
    "lavoro": MemoryCategory.work.value,
    "progetti": MemoryCategory.projects.value,
    "preferenze": MemoryCategory.preferences.value,
    "note": MemoryCategory.other.value,
}


def normalize_category(value: Any) -> str:
    if isinstance(value, MemoryCategory):
        return value.value
    if isinstance(value, str):
        if value in LEGACY_CATEGORY_MAP:
            return LEGACY_CATEGORY_MAP[value]
        try:
            return MemoryCategory(value).value
        except ValueError:
            pass
    raise ValueError("Invalid memory category")


class MemoryWrite(BaseModel):
    """Full memory input with optional fields for older API clients."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1, max_length=20_000)
    category: MemoryCategory
    source_type: MemorySourceType | None = None
    source: str | None = Field(default=None, max_length=200)
    verification: MemoryVerification | None = None
    tags: list[str] | None = Field(default=None, max_length=30)
    importance: int | None = Field(default=None, ge=1, le=5)
    excluded: bool | None = None
    conversation_id: str | None = Field(default=None, max_length=120)

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category_value(cls, value: Any) -> str:
        return normalize_category(value)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized: list[str] = []
        for tag in value:
            tag = tag.strip()
            if not tag or len(tag) > 64:
                raise ValueError("Invalid tag")
            normalized.append(tag)
        return normalized

    @model_validator(mode="after")
    def reject_null_non_nullable_metadata(self) -> MemoryWrite:
        for field_name in (
            "source_type",
            "verification",
            "tags",
            "importance",
            "excluded",
        ):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError("Invalid memory metadata")
        return self


class MemoryRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    content: str
    category: MemoryCategory
    source_type: MemorySourceType
    source: str | None
    verification: MemoryVerification
    tags: list[str]
    importance: int = Field(ge=1, le=5)
    excluded: bool
    conversation_id: str | None
    last_used: datetime | None
    created_at: datetime
    updated_at: datetime


class MemoryLinkWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    from_id: str = Field(min_length=1, max_length=120)
    to_id: str = Field(min_length=1, max_length=120)
    relation: str = Field(min_length=1, max_length=120)
    strength: int = Field(default=2, ge=1, le=3)

    @model_validator(mode="after")
    def reject_self_link(self) -> MemoryLinkWrite:
        if self.from_id == self.to_id:
            raise ValueError("Self-links are not allowed")
        return self


class MemoryLinkRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    from_id: str
    to_id: str
    relation: str
    strength: int = Field(ge=1, le=3)
    created_at: datetime


class MemoryGraphRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nodes: list[MemoryRead]
    edges: list[MemoryLinkRead]


class MemoryExclusionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    excluded: bool
