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

    # ------------------------------------------------------------------
    # Agent-to-mission assignments (M5 Punto 3)
    # ------------------------------------------------------------------

    def assign_agent_to_mission(
        self,
        *,
        agent_kind: str,
        agent_id: str,
        mission_id: str,
        assigned_by_kind: str,
        assigned_by_id: str,
    ) -> dict[str, Any]:
        if agent_kind not in _IDENTITY_KINDS:
            raise ValueError("Agent kind is not valid.")
        if not _valid_identifier(agent_id):
            raise ValueError("Agent identifier is not valid.")
        if not _valid_identifier(mission_id):
            raise ValueError("Mission identifier is not valid.")
        if assigned_by_kind not in _IDENTITY_KINDS:
            raise ValueError("Assigner kind is not valid.")
        if not _valid_identifier(assigned_by_id):
            raise ValueError("Assigner identifier is not valid.")
        return self._repository.assign_agent_to_mission(
            agent_kind=agent_kind,
            agent_id=agent_id,
            mission_id=mission_id,
            assigned_by_kind=assigned_by_kind,
            assigned_by_id=assigned_by_id,
        )

    def revoke_agent_from_mission(
        self,
        *,
        assignment_id: str,
        revoked_by_kind: str,
        revoked_by_id: str,
    ) -> dict[str, Any] | None:
        if not _valid_identifier(assignment_id):
            raise ValueError("Assignment identifier is not valid.")
        if revoked_by_kind not in _IDENTITY_KINDS:
            raise ValueError("Revoker kind is not valid.")
        if not _valid_identifier(revoked_by_id):
            raise ValueError("Revoker identifier is not valid.")
        return self._repository.revoke_agent_from_mission(
            assignment_id=assignment_id,
            revoked_by_kind=revoked_by_kind,
            revoked_by_id=revoked_by_id,
        )

    def get_agent_assignment(
        self,
        assignment_id: str,
    ) -> dict[str, Any] | None:
        if not _valid_identifier(assignment_id):
            raise ValueError("Assignment identifier is not valid.")
        return self._repository.get_agent_assignment(assignment_id)

    def list_agent_assignments(
        self,
        *,
        agent_kind: str | None = None,
        agent_id: str | None = None,
        mission_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if agent_kind is not None and agent_kind not in _IDENTITY_KINDS:
            raise ValueError("Agent kind is not valid.")
        if agent_id is not None and not _valid_identifier(agent_id):
            raise ValueError("Agent identifier is not valid.")
        if mission_id is not None and not _valid_identifier(mission_id):
            raise ValueError("Mission identifier is not valid.")
        if status is not None and status not in {"active", "revoked"}:
            raise ValueError("Assignment status is not valid.")
        return self._repository.list_agent_assignments(
            agent_kind=agent_kind,
            agent_id=agent_id,
            mission_id=mission_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    # ------------------------------------------------------------------
    # Background tasks (M5 Punto 4 — Execution Plane)
    # ------------------------------------------------------------------

    def create_background_task(
        self,
        *,
        task_type: str,
        payload: dict[str, Any],
        timeout_seconds: int = 300,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        if not task_type or not task_type.strip():
            raise ValueError("Task type is required.")
        if timeout_seconds < 1 or timeout_seconds > 86400:
            raise ValueError("Timeout must be between 1 and 86400 seconds.")
        if max_retries < 0 or max_retries > 100:
            raise ValueError("Max retries must be between 0 and 100.")
        return self._repository.create_background_task(
            task_type=task_type,
            payload=payload,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

    def get_background_task(self, task_id: str) -> dict[str, Any] | None:
        if not _valid_identifier(task_id):
            raise ValueError("Task identifier is not valid.")
        return self._repository.get_background_task(task_id)

    def list_background_tasks(
        self,
        *,
        task_type: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if status is not None and status not in {
            "pending", "running", "completed", "cancelled", "failed"
        }:
            raise ValueError("Task status is not valid.")
        return self._repository.list_background_tasks(
            task_type=task_type,
            status=status,
            limit=limit,
            offset=offset,
        )

    def update_background_task_status(
        self,
        *,
        task_id: str,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> dict[str, Any] | None:
        if not _valid_identifier(task_id):
            raise ValueError("Task identifier is not valid.")
        return self._repository.update_background_task_status(
            task_id=task_id,
            status=status,
            result=result,
            error=error,
        )

    def cancel_background_task(self, task_id: str) -> dict[str, Any] | None:
        if not _valid_identifier(task_id):
            raise ValueError("Task identifier is not valid.")
        return self._repository.cancel_background_task(task_id=task_id)

    def list_overdue_tasks(self) -> list[dict[str, Any]]:
        return self._repository.list_overdue_tasks()

    def increment_retry_count(self, task_id: str) -> dict[str, Any] | None:
        if not _valid_identifier(task_id):
            raise ValueError("Task identifier is not valid.")
        return self._repository.increment_retry_count(task_id=task_id)

    # ------------------------------------------------------------------
    # Evolution Lab patch proposals (M5 Punto 5)
    # ------------------------------------------------------------------

    def create_patch_proposal(
        self,
        *,
        title: str,
        description: str,
        target_file: str,
        patch_content: str,
        proposed_by_kind: str,
        proposed_by_id: str,
    ) -> dict[str, Any]:
        if not title or not title.strip():
            raise ValueError("Proposal title is required.")
        if not description or not description.strip():
            raise ValueError("Proposal description is required.")
        if not target_file or not target_file.strip():
            raise ValueError("Target file is required.")
        if not patch_content or not patch_content.strip():
            raise ValueError("Patch content is required.")
        if proposed_by_kind not in _IDENTITY_KINDS:
            raise ValueError("Proposer kind is not valid.")
        if not _valid_identifier(proposed_by_id):
            raise ValueError("Proposer identifier is not valid.")
        return self._repository.create_patch_proposal(
            title=title.strip(),
            description=description.strip(),
            target_file=target_file.strip(),
            patch_content=patch_content,
            proposed_by_kind=proposed_by_kind,
            proposed_by_id=proposed_by_id,
        )

    def get_patch_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        if not _valid_identifier(proposal_id):
            raise ValueError("Proposal identifier is not valid.")
        return self._repository.get_patch_proposal(proposal_id)

    def list_patch_proposals(
        self,
        *,
        status: str | None = None,
        proposed_by_kind: str | None = None,
        proposed_by_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if status is not None and status not in {"pending", "approved", "rejected"}:
            raise ValueError("Proposal status is not valid.")
        if proposed_by_kind is not None and proposed_by_kind not in _IDENTITY_KINDS:
            raise ValueError("Proposer kind is not valid.")
        if proposed_by_id is not None and not _valid_identifier(proposed_by_id):
            raise ValueError("Proposer identifier is not valid.")
        return self._repository.list_patch_proposals(
            status=status,
            proposed_by_kind=proposed_by_kind,
            proposed_by_id=proposed_by_id,
            limit=limit,
            offset=offset,
        )

    def approve_patch_proposal(
        self,
        *,
        proposal_id: str,
        reviewed_by_kind: str,
        reviewed_by_id: str,
        approval_reason: str,
    ) -> dict[str, Any] | None:
        if not _valid_identifier(proposal_id):
            raise ValueError("Proposal identifier is not valid.")
        if reviewed_by_kind not in _IDENTITY_KINDS:
            raise ValueError("Reviewer kind is not valid.")
        if not _valid_identifier(reviewed_by_id):
            raise ValueError("Reviewer identifier is not valid.")
        if not approval_reason or not approval_reason.strip():
            raise ValueError("Approval reason is required.")
        return self._repository.approve_patch_proposal(
            proposal_id=proposal_id,
            reviewed_by_kind=reviewed_by_kind,
            reviewed_by_id=reviewed_by_id,
            approval_reason=approval_reason.strip(),
        )

    def reject_patch_proposal(
        self,
        *,
        proposal_id: str,
        reviewed_by_kind: str,
        reviewed_by_id: str,
        rejection_reason: str,
    ) -> dict[str, Any] | None:
        if not _valid_identifier(proposal_id):
            raise ValueError("Proposal identifier is not valid.")
        if reviewed_by_kind not in _IDENTITY_KINDS:
            raise ValueError("Reviewer kind is not valid.")
        if not _valid_identifier(reviewed_by_id):
            raise ValueError("Reviewer identifier is not valid.")
        if not rejection_reason or not rejection_reason.strip():
            raise ValueError("Rejection reason is required.")
        return self._repository.reject_patch_proposal(
            proposal_id=proposal_id,
            reviewed_by_kind=reviewed_by_kind,
            reviewed_by_id=reviewed_by_id,
            rejection_reason=rejection_reason.strip(),
        )

    # ------------------------------------------------------------------
    # General preferences (M5 Punto 6 — Settings e Network Center)
    # ------------------------------------------------------------------

    def get_preference(self, key: str) -> dict[str, Any] | None:
        if not key or not key.strip():
            raise ValueError("Preference key is required.")
        return self._repository.get_preference(key.strip())

    def set_preference(
        self,
        *,
        key: str,
        value: Any,
        updated_by_kind: str,
        updated_by_id: str,
    ) -> dict[str, Any]:
        if not key or not key.strip():
            raise ValueError("Preference key is required.")
        if updated_by_kind not in _IDENTITY_KINDS:
            raise ValueError("Updater kind is not valid.")
        if not _valid_identifier(updated_by_id):
            raise ValueError("Updater identifier is not valid.")
        return self._repository.set_preference(
            key=key.strip(),
            value=value,
            updated_by_kind=updated_by_kind,
            updated_by_id=updated_by_id,
        )

    def list_preferences(self) -> list[dict[str, Any]]:
        return self._repository.list_preferences()


def _valid_identifier(value: Any) -> bool:
    return isinstance(value, str) and _IDENTIFIER.fullmatch(value) is not None
