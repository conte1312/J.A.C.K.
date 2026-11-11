from __future__ import annotations

import json
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

IdentityKindValue = Literal["user", "agent", "service", "tool", "node"]
RiskLevelValue = Literal["low", "normal", "high", "critical"]
Operation = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[a-z][a-z0-9._:-]*$")]


def _validate_scope(value: dict[str, object]) -> dict[str, object]:
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as error:
        raise ValueError("Scope must contain JSON values.") from error
    if len(encoded) > 16_384:
        raise ValueError("Scope is too large.")
    return value


Scope = Annotated[dict[str, object], AfterValidator(_validate_scope)]


class ControlPlaneWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IdentityRef(ControlPlaneWrite):
    kind: IdentityKindValue
    id: str = Field(min_length=2, max_length=128, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:-]*$")


class IdentityDeclaration(ControlPlaneWrite):
    kind: IdentityKindValue
    id: str = Field(min_length=2, max_length=128, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:-]*$")
    display_name: str = Field(min_length=1, max_length=200)


class IdentityRead(IdentityDeclaration):
    declared_at: str


class CapabilityDeclaration(ControlPlaneWrite):
    id: str = Field(min_length=2, max_length=128, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:-]*$")
    owner: IdentityRef
    description: str = Field(min_length=1, max_length=2000)
    resource: str = Field(min_length=1, max_length=256)
    operations: list[Operation] = Field(min_length=1, max_length=50)
    scope: Scope = Field(default_factory=dict)
    risk_level: RiskLevelValue
    approval_required: bool

    @model_validator(mode="after")
    def validate_declaration(self) -> CapabilityDeclaration:
        if len(set(self.operations)) != len(self.operations):
            raise ValueError("Capability operations must be unique.")
        if self.risk_level == "critical" and not self.approval_required:
            raise ValueError("Critical declarations require approval.")
        return self


class CapabilityRead(CapabilityDeclaration):
    declared_at: str


class PermissionRequestContract(ControlPlaneWrite):
    """Data contract only; this phase does not evaluate or grant requests."""

    requester: IdentityRef
    resource: str = Field(min_length=2, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    operation: str = Field(min_length=1, max_length=128)
    scope: Scope = Field(default_factory=dict)
    duration_seconds: int | None = Field(default=None, gt=0, le=31_536_000)
    risk_level: RiskLevelValue


class PolicyRuleContract(ControlPlaneWrite):
    """Declarative rule shape only; no rule is applied in this phase."""

    id: str = Field(min_length=2, max_length=128)
    resource: str = Field(min_length=2, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    operation: str = Field(min_length=1, max_length=128)
    requester_kind: IdentityKindValue | None = None
    scope: Scope = Field(default_factory=dict)
    outcome: Literal["deny", "requires_approval", "allow"]
    risk_level: RiskLevelValue
    approval_required: bool


class AuthorizationDecisionContract(ControlPlaneWrite):
    """Decision result shape only; this phase does not produce decisions."""

    outcome: Literal["deny", "requires_approval", "allow"]
    policy_id: str | None = None
    approval_required: bool
    valid_until: str | None = None
    reason: str = Field(max_length=2000)

    @model_validator(mode="after")
    def validate_approval_requirement(self) -> AuthorizationDecisionContract:
        if self.outcome == "requires_approval" and not self.approval_required:
            raise ValueError("Approval decisions must require approval.")
        return self


class ApprovalRecordContract(ControlPlaneWrite):
    """Approval data contract only; approvals are not actionable in this phase."""

    id: str = Field(min_length=2, max_length=128)
    request_id: str = Field(min_length=2, max_length=128)
    status: Literal["pending", "approved", "rejected", "expired"]
    requested_by: IdentityRef
    resolved_by: IdentityRef | None = None
    expires_at: str | None = None

    @model_validator(mode="after")
    def validate_resolution(self) -> ApprovalRecordContract:
        if self.status in {"approved", "rejected"} and self.resolved_by is None:
            raise ValueError("Resolved approvals require a resolving identity.")
        if self.status == "pending" and self.resolved_by is not None:
            raise ValueError("Pending approvals cannot have a resolving identity.")
        return self


class EmergencyStopStatusContract(ControlPlaneWrite):
    """Read-model contract; no emergency-stop state or control is exposed."""

    active: bool
    activated_at: str | None = None
    activated_by: IdentityRef | None = None
    reason: str | None = Field(default=None, max_length=2000)


class AuditEventRead(ControlPlaneWrite):
    id: str
    occurred_at: str
    actor: IdentityRef
    action: str
    subject: IdentityRef
    outcome: Literal["recorded"]
    details: dict[str, object]


class AgentProfileRead(ControlPlaneWrite):
    id: str
    name: str
    description: str
    division: str
    source_repository: str
    source_revision: str
    source_file: str
    source_url: str
    source_license: Literal["MIT"]
    enabled: Literal[False]
    execution_enabled: Literal[False]
    capabilities: list[str]
    tools: list[str]


class AgentProfileDetailRead(AgentProfileRead):
    profile_markdown: str


# ---------------------------------------------------------------------------
# Agent-to-mission assignments (M5 Punto 3)
# ---------------------------------------------------------------------------

class AgentAssignmentCreate(ControlPlaneWrite):
    agent_kind: IdentityKindValue
    agent_id: str = Field(min_length=2, max_length=128, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:-]*$")
    mission_id: str = Field(min_length=2, max_length=128, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:-]*$")
    assigned_by_kind: IdentityKindValue
    assigned_by_id: str = Field(min_length=2, max_length=128, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:-]*$")


class AgentAssignmentRead(ControlPlaneWrite):
    id: str
    agent: IdentityRef
    mission_id: str
    assigned_at: str
    assigned_by: IdentityRef
    status: Literal["active", "revoked"]


class AgentAssignmentList(ControlPlaneWrite):
    assignments: list[AgentAssignmentRead]
    total: int


# ---------------------------------------------------------------------------
# Background tasks (M5 Punto 4 — Execution Plane)
# ---------------------------------------------------------------------------

class BackgroundTaskCreate(ControlPlaneWrite):
    task_type: str = Field(min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=300, ge=1, le=86400)
    max_retries: int = Field(default=3, ge=0, le=100)


class BackgroundTaskStatusUpdate(ControlPlaneWrite):
    status: Literal["pending", "running", "completed", "cancelled", "failed"]
    result: dict[str, Any] | None = None
    error: str | None = Field(default=None, max_length=4000)


class BackgroundTaskRead(ControlPlaneWrite):
    id: str
    task_type: str
    payload: dict[str, Any]
    status: Literal["pending", "running", "completed", "cancelled", "failed"]
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    timeout_seconds: int
    max_retries: int
    retry_count: int


    reviewed_by: IdentityRef | None = None
    reviewed_at: str | None = None
    approval_reason: str | None = None


# Rebuild all Pydantic models that use forward references or typing.Any.
BackgroundTaskCreate.model_rebuild()
BackgroundTaskStatusUpdate.model_rebuild()
BackgroundTaskRead.model_rebuild()


# ---------------------------------------------------------------------------
# Evolution Lab patch proposals (M5 Punto 5)
# ---------------------------------------------------------------------------

class PatchProposalCreate(ControlPlaneWrite):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    target_file: str = Field(min_length=1, max_length=500)
    patch_content: str = Field(min_length=1)
    proposed_by_kind: IdentityKindValue
    proposed_by_id: str = Field(min_length=2, max_length=128, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:-]*$")


class PatchProposalRead(ControlPlaneWrite):
    id: str
    title: str
    description: str
    target_file: str
    patch_content: str
    status: Literal["pending", "approved", "rejected"]
    proposed_by: IdentityRef
    proposed_at: str
    reviewed_by: IdentityRef | None = None
    reviewed_at: str | None = None
    approval_reason: str | None = None


# Rebuild all Pydantic models that use forward references or typing.Any.
BackgroundTaskCreate.model_rebuild()
BackgroundTaskStatusUpdate.model_rebuild()
BackgroundTaskRead.model_rebuild()
PatchProposalCreate.model_rebuild()
PatchProposalRead.model_rebuild()


# ---------------------------------------------------------------------------
# General preferences (M5 Punto 6 — Settings e Network Center)
# ---------------------------------------------------------------------------

class PreferenceGet(ControlPlaneWrite):
    key: str
    value: Any
    updated_at: str


class PreferenceSet(ControlPlaneWrite):
    value: Any


class PreferenceList(ControlPlaneWrite):
    preferences: list[PreferenceGet]


# Rebuild preference models that use typing.Any.
PreferenceGet.model_rebuild()
PreferenceSet.model_rebuild()
PreferenceList.model_rebuild()
