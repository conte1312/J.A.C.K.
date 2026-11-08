from __future__ import annotations

import json
import re
from typing import Any

from app.control_plane.repository import ControlPlaneRepository

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{1,127}$")
_OPERATION = re.compile(r"^[a-z][a-z0-9._:-]{0,127}$")
_RISK_LEVELS = {"low", "normal", "high", "critical"}
_IDENTITY_KINDS = {"user", "agent", "service", "tool", "node"}
_MAX_SCOPE_BYTES = 16_384


class ControlPlaneService:
    """Validates declarations; it deliberately makes no authorization decisions."""

    def __init__(self, repository: ControlPlaneRepository) -> None:
        self._repository = repository

    def declare_identity(self, declaration: dict[str, Any]) -> dict[str, Any]:
        kind = declaration.get("kind")
        identity_id = declaration.get("id")
        display_name = declaration.get("display_name")
        if kind not in _IDENTITY_KINDS:
            raise ValueError("Identity kind is not valid.")
        if not isinstance(identity_id, str) or not _IDENTIFIER.fullmatch(identity_id):
            raise ValueError("Identity identifier is not valid.")
        if not isinstance(display_name, str) or not display_name.strip():
            raise ValueError("Identity display name is required.")
        return self._repository.declare_identity(
            {**declaration, "display_name": display_name.strip()}
        )

    def list_identities(
        self, *, kind: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[dict[str, Any]]:
        if kind is not None and kind not in _IDENTITY_KINDS:
            raise ValueError("Identity kind is not valid.")
        return self._repository.list_identities(kind=kind, limit=limit, offset=offset)

    def declare_capability(self, declaration: dict[str, Any]) -> dict[str, Any]:
        if not _valid_identifier(declaration.get("id")):
            raise ValueError("Capability identifier is not valid.")
        owner = declaration.get("owner")
        if not isinstance(owner, dict) or owner.get("kind") not in _IDENTITY_KINDS:
            raise ValueError("Capability owner identity is not valid.")
        if not _valid_identifier(owner.get("id")):
            raise ValueError("Capability owner identifier is not valid.")
        if not str(declaration.get("description", "")).strip():
            raise ValueError("Capability description is required.")
        resource = declaration.get("resource")
        if not isinstance(resource, str) or not _valid_identifier(resource):
            raise ValueError("Capability resource is not valid.")
        operations = declaration.get("operations")
        if (
            not isinstance(operations, list)
            or not operations
            or len(operations) > 50
            or any(
                not isinstance(item, str) or not _OPERATION.fullmatch(item)
                for item in operations
            )
            or len(set(operations)) != len(operations)
        ):
            raise ValueError("Capability operations must be unique valid identifiers.")
        if declaration.get("risk_level") not in _RISK_LEVELS:
            raise ValueError("Capability risk level is not valid.")
        if not isinstance(declaration.get("approval_required"), bool):
            raise ValueError("Capability approval_required must be a boolean.")
        scope = declaration.get("scope")
        if not isinstance(scope, dict):
            raise ValueError("Capability scope must be an object.")
        try:
            scope_size = len(
                json.dumps(
                    scope,
                    ensure_ascii=False,
                    allow_nan=False,
                ).encode("utf-8")
            )
        except (TypeError, ValueError, RecursionError) as error:
            raise ValueError("Capability scope must contain JSON values.") from error
        if scope_size > _MAX_SCOPE_BYTES:
            raise ValueError("Capability scope is too large.")
        if (
            declaration.get("risk_level") == "critical"
            and not declaration["approval_required"]
        ):
            raise ValueError(
                "Critical declarations must state that approval is required."
            )
        return self._repository.declare_capability(declaration)

    def list_capabilities(
        self,
        *,
        owner_kind: str | None = None,
        owner_id: str | None = None,
        resource: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if owner_kind is not None and owner_kind not in _IDENTITY_KINDS:
            raise ValueError("Capability owner kind is not valid.")
        if owner_id is not None and not _valid_identifier(owner_id):
            raise ValueError("Capability owner identifier is not valid.")
        if resource is not None and not _valid_identifier(resource):
            raise ValueError("Capability resource is not valid.")
        return self._repository.list_capabilities(
            owner_kind=owner_kind,
            owner_id=owner_id,
            resource=resource,
            limit=limit,
            offset=offset,
        )

    def list_audit_events(
        self,
        *,
        subject_kind: str | None = None,
        subject_id: str | None = None,
        action: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if subject_kind is not None and subject_kind not in _IDENTITY_KINDS:
            raise ValueError("Audit subject kind is not valid.")
        if subject_id is not None and not _valid_identifier(subject_id):
            raise ValueError("Audit subject identifier is not valid.")
        if action is not None and not _valid_identifier(action):
            raise ValueError("Audit action is not valid.")
        return self._repository.list_audit_events(
            subject_kind=subject_kind,
            subject_id=subject_id,
            action=action,
            limit=limit,
            offset=offset,
        )


def _valid_identifier(value: Any) -> bool:
    return isinstance(value, str) and _IDENTIFIER.fullmatch(value) is not None
