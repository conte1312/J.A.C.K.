from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TaskState = Literal[
    "inbox", "todo", "in_progress", "blocked", "completed", "cancelled"
]
Priority = Literal["low", "normal", "high", "critical"]
Recurrence = Literal["none", "daily", "weekly", "monthly"]


class PlanningWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskCreate(PlanningWrite):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=20_000)
    status: TaskState = "inbox"
    priority: Priority = "normal"
    category: str = Field(default="", max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=50)
    start_date: str | None = None
    due_date: str | None = None
    project_id: str | None = None
    mission_id: str | None = None
    recurrence_kind: Recurrence = "none"
    recurrence_interval: int = Field(default=1, ge=1, le=365)
    ai_origin: bool = False
    responsible_agent: str | None = Field(default=None, max_length=200)
    notes: str = Field(default="", max_length=20_000)
    position: int = 0


class TaskUpdate(PlanningWrite):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=20_000)
    status: TaskState | None = None
    priority: Priority | None = None
    category: str | None = Field(default=None, max_length=100)
    tags: list[str] | None = Field(default=None, max_length=50)
    start_date: str | None = None
    due_date: str | None = None
    project_id: str | None = None
    mission_id: str | None = None
    recurrence_kind: Recurrence | None = None
    recurrence_interval: int | None = Field(default=None, ge=1, le=365)
    responsible_agent: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=20_000)
    position: int | None = None


class ProjectCreate(PlanningWrite):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=20_000)
    goal: str = Field(default="", max_length=20_000)
    status: Literal["active", "on_hold", "completed", "archived"] = "active"
    priority: Priority = "normal"
    start_date: str | None = None
    due_date: str | None = None
    notes: str = Field(default="", max_length=20_000)


class ProjectUpdate(PlanningWrite):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=20_000)
    goal: str | None = Field(default=None, max_length=20_000)
    status: Literal["active", "on_hold", "completed", "archived"] | None = None
    priority: Priority | None = None
    start_date: str | None = None
    due_date: str | None = None
    notes: str | None = Field(default=None, max_length=20_000)


class MilestoneCreate(PlanningWrite):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=20_000)
    due_date: str | None = None
    position: int = 0


class MilestoneUpdate(PlanningWrite):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=20_000)
    due_date: str | None = None
    completed_at: str | None = None
    position: int | None = None


class EventCreate(PlanningWrite):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=20_000)
    starts_at: str
    ends_at: str
    timezone: str = Field(min_length=1, max_length=100)
    priority: Priority = "normal"
    project_id: str | None = None
    recurrence_kind: Recurrence = "none"
    recurrence_interval: int = Field(default=1, ge=1, le=365)
    recurrence_until: str | None = None


class EventUpdate(PlanningWrite):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=20_000)
    starts_at: str | None = None
    ends_at: str | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=100)
    priority: Priority | None = None
    project_id: str | None = None
    recurrence_kind: Recurrence | None = None
    recurrence_interval: int | None = Field(default=None, ge=1, le=365)
    recurrence_until: str | None = None


class CalendarPreferencesUpdate(PlanningWrite):
    timezone: str = Field(min_length=1, max_length=100)


class AiInterpretRequest(PlanningWrite):
    text: str = Field(min_length=1, max_length=10_000)


class AiApplyRequest(PlanningWrite):
    proposal_id: str = Field(min_length=1, max_length=100)
    confirmed: bool


class MissionCreate(PlanningWrite):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=20_000)
    plan: str = Field(default="", max_length=20_000)
    status: Literal["planned", "pending_approval", "approved", "cancelled"] = "planned"
    assigned_agents: list[str] = Field(default_factory=list, max_length=50)
    results: str = Field(default="", max_length=20_000)
    notes: str = Field(default="", max_length=20_000)


class MissionUpdate(PlanningWrite):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=20_000)
    plan: str | None = Field(default=None, max_length=20_000)
    status: Literal["planned", "pending_approval", "approved", "cancelled"] | None = None
    assigned_agents: list[str] | None = Field(default=None, max_length=50)
    results: str | None = Field(default=None, max_length=20_000)
    notes: str | None = Field(default=None, max_length=20_000)


class MissionLogCreate(PlanningWrite):
    message: str = Field(min_length=1, max_length=20_000)


class MissionApprovalCreate(PlanningWrite):
    description: str = Field(min_length=1, max_length=2_000)


class MissionApprovalUpdate(PlanningWrite):
    status: Literal["pending", "approved", "rejected"]
