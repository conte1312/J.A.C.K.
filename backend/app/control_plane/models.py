from __future__ import annotations

from enum import Enum


class IdentityKind(str, Enum):
    USER = "user"
    AGENT = "agent"
    SERVICE = "service"
    TOOL = "tool"
    NODE = "node"


class RiskLevel(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class AuthorizationOutcome(str, Enum):
    DENY = "deny"
    REQUIRES_APPROVAL = "requires_approval"
    ALLOW = "allow"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
