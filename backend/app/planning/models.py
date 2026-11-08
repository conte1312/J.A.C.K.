from __future__ import annotations

"""Modelli di dominio del motore di pianificazione di J.A.C.K.

Tutti i modelli sono puri (nessuna dipendenza da FastAPI/SQLAlchemy) e
serializzabili tramite metodi `to_dict` / `from_dict` per il layer API e
la persistenza SQLite.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from typing import Any, Optional
import uuid


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _new_id() -> str:
    return str(uuid.uuid4())


class TaskStatus(str, Enum):
    INBOX = "inbox"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

    @classmethod
    def values(cls) -> list[str]:
        return [e.value for e in cls]


class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def values(cls) -> list[str]:
        return [e.value for e in cls]


class RecurrenceKind(str, Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class ChecklistItem:
    id: str
    task_id: str
    title: str
    is_done: bool = False
    position: int = 0
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "title": self.title,
            "is_done": int(self.is_done),
            "position": self.position,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChecklistItem":
        return cls(
            id=data["id"],
            task_id=data["task_id"],
            title=data["title"],
            is_done=bool(data.get("is_done", 0)),
            position=int(data.get("position", 0)),
            created_at=data.get("created_at", _now()),
        )


@dataclass
class TaskDependency:
    id: str
    task_id: str
    depends_on_task_id: str
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "depends_on_task_id": self.depends_on_task_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskDependency":
        return cls(
            id=data["id"],
            task_id=data["task_id"],
            depends_on_task_id=data["depends_on_task_id"],
            created_at=data.get("created_at", _now()),
        )


@dataclass
class Task:
    id: str
    title: str
    description: str = ""
    status: str = TaskStatus.INBOX.value
    priority: str = TaskPriority.NORMAL.value
    category: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    start_date: Optional[str] = None
    due_date: Optional[str] = None
    completed_at: Optional[str] = None
    project_id: Optional[str] = None
    mission_id: Optional[str] = None
    recurrence_kind: str = RecurrenceKind.NONE.value
    recurrence_interval: int = 1
    recurrence_series_id: Optional[str] = None
    ai_origin: bool = False
    responsible_agent: Optional[str] = None
    notes: str = ""
    position: int = 0

    def to_dict(self, include_checklist: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "category": self.category,
            "tags": self.tags,
            "created_at": self.created_at,
            "start_date": self.start_date,
            "due_date": self.due_date,
            "completed_at": self.completed_at,
            "project_id": self.project_id,
            "mission_id": self.mission_id,
            "recurrence_kind": self.recurrence_kind,
            "recurrence_interval": self.recurrence_interval,
            "recurrence_series_id": self.recurrence_series_id,
            "ai_origin": int(self.ai_origin),
            "responsible_agent": self.responsible_agent,
            "notes": self.notes,
            "position": self.position,
        }
        if include_checklist:
            data["checklist"] = [i.to_dict() for i in self.checklist or []]
            data["dependencies"] = [d.to_dict() for d in self.dependencies or []]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            status=data.get("status", TaskStatus.INBOX.value),
            priority=data.get("priority", TaskPriority.NORMAL.value),
            category=data.get("category", ""),
            tags=list(data.get("tags") or []),
            created_at=data.get("created_at", _now()),
            start_date=data.get("start_date"),
            due_date=data.get("due_date"),
            completed_at=data.get("completed_at"),
            project_id=data.get("project_id"),
            mission_id=data.get("mission_id"),
            recurrence_kind=data.get("recurrence_kind", RecurrenceKind.NONE.value),
            recurrence_interval=int(data.get("recurrence_interval", 1)),
            recurrence_series_id=data.get("recurrence_series_id"),
            ai_origin=bool(data.get("ai_origin", 0)),
            responsible_agent=data.get("responsible_agent"),
            notes=data.get("notes", ""),
            position=int(data.get("position", 0)),
        )

    # Campi popolati dal servizio (non persistiti direttamente nelle colonne base)
    checklist: list[ChecklistItem] = field(default_factory=list, repr=False)
    dependencies: list[TaskDependency] = field(default_factory=list, repr=False)
    dependents: list[str] = field(default_factory=list, repr=False)

    @property
    def is_completed(self) -> bool:
        return self.status == TaskStatus.COMPLETED.value

    @property
    def is_overdue(self) -> bool:
        if self.due_date is None or self.is_completed:
            return False
        return self.due_date < _now()[:10]


@dataclass
class Project:
    id: str
    name: str
    description: str = ""
    goal: str = ""
    status: str = "active"
    priority: str = TaskPriority.NORMAL.value
    start_date: Optional[str] = None
    due_date: Optional[str] = None
    notes: str = ""
    created_at: str = field(default_factory=_now)
    archived_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "goal": self.goal,
            "status": self.status,
            "priority": self.priority,
            "start_date": self.start_date,
            "due_date": self.due_date,
            "notes": self.notes,
            "created_at": self.created_at,
            "archived_at": self.archived_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Project":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            goal=data.get("goal", ""),
            status=data.get("status", "active"),
            priority=data.get("priority", TaskPriority.NORMAL.value),
            start_date=data.get("start_date"),
            due_date=data.get("due_date"),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", _now()),
            archived_at=data.get("archived_at"),
        )

    # Popolato dal servizio
    task_ids: list[str] = field(default_factory=list, repr=False)
    completion_percent: int = 0
    open_task_count: int = 0
    completed_task_count: int = 0
    milestones: list[dict[str, Any]] = field(default_factory=list, repr=False)

    @property
    def is_archived(self) -> bool:
        return self.status == "archived" or self.archived_at is not None

    def to_dict_with_stats(self) -> dict[str, Any]:
        data = self.to_dict()
        data["task_ids"] = list(self.task_ids)
        data["completion_percent"] = int(self.completion_percent)
        data["open_task_count"] = int(self.open_task_count)
        data["completed_task_count"] = int(self.completed_task_count)
        data["milestones"] = list(self.milestones)
        return data


@dataclass
class Mission:
    id: str
    title: str
    description: str = ""
    plan: str = ""
    status: str = "planned"
    progress_percent: int = 0
    created_at: str = field(default_factory=_now)
    completed_at: Optional[str] = None
    notes: str = ""
    assigned_agents: list[str] = field(default_factory=list)
    results: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "plan": self.plan,
            "status": self.status,
            "progress_percent": self.progress_percent,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "notes": self.notes,
            "assigned_agents": self.assigned_agents,
            "results": self.results,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Mission":
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            plan=data.get("plan", ""),
            status=data.get("status", "planned"),
            progress_percent=int(data.get("progress_percent", 0)),
            created_at=data.get("created_at", _now()),
            completed_at=data.get("completed_at"),
            notes=data.get("notes", ""),
            assigned_agents=list(
                json.loads(data.get("assigned_agents", "[]"))
                if isinstance(data.get("assigned_agents", "[]"), str)
                else data.get("assigned_agents", [])
            ),
            results=data.get("results", ""),
        )

    task_ids: list[str] = field(default_factory=list, repr=False)
    progress_percent: int = 0
    logs: list[dict[str, Any]] = field(default_factory=list, repr=False)
    approvals: list[dict[str, Any]] = field(default_factory=list, repr=False)

    def to_dict_with_stats(self) -> dict[str, Any]:
        data = self.to_dict()
        data["task_ids"] = list(self.task_ids)
        data["progress_percent"] = int(self.progress_percent)
        data["logs"] = list(self.logs)
        data["approvals"] = list(self.approvals)
        return data
