from __future__ import annotations

import json
from typing import Annotated, Literal

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
