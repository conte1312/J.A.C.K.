from __future__ import annotations

"""Repository SQLite per il motore di pianificazione di J.A.C.K.

Usa un file di database separato (`tasks.sqlite3`) nella stessa directory
della memoria locale, in modo da non toccare né sovrascrivere i dati
esistenti di `memories.sqlite3`.
"""

import json
import logging
import os
import sqlite3
import sys
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from app.planning.models import (
    ChecklistItem,
    Mission,
    Project,
    RecurrenceKind,
    Task,
    TaskDependency,
    TaskPriority,
    TaskStatus,
    _new_id,
)

logger = logging.getLogger("jack.backend.planning")

SCHEMA_VERSION = 4

TASKS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL CHECK(length(trim(title)) BETWEEN 1 AND 200),
        description TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL CHECK(status IN (
            'inbox', 'todo', 'in_progress', 'blocked', 'completed', 'cancelled'
        )),
        priority TEXT NOT NULL CHECK(priority IN ('low', 'normal', 'high', 'critical')),
        category TEXT NOT NULL DEFAULT '',
        tags TEXT NOT NULL DEFAULT '[]',
        created_at TEXT NOT NULL,
        start_date TEXT,
        due_date TEXT,
        completed_at TEXT,
        project_id TEXT,
        mission_id TEXT,
        recurrence_kind TEXT NOT NULL DEFAULT 'none' CHECK(recurrence_kind IN ('none', 'daily', 'weekly', 'monthly')),
        recurrence_interval INTEGER NOT NULL DEFAULT 1 CHECK(recurrence_interval >= 1),
        recurrence_series_id TEXT,
        ai_origin INTEGER NOT NULL DEFAULT 0 CHECK(ai_origin IN (0, 1)),
        responsible_agent TEXT,
        notes TEXT NOT NULL DEFAULT '',
        position INTEGER NOT NULL DEFAULT 0
    )
"""

PROJECTS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 200),
        description TEXT NOT NULL DEFAULT '',
        goal TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'active',
        priority TEXT NOT NULL DEFAULT 'normal',
        start_date TEXT,
        due_date TEXT,
        notes TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        archived_at TEXT
    )
"""

CHECKLIST_ITEMS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS checklist_items (
        id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
        title TEXT NOT NULL CHECK(length(trim(title)) BETWEEN 1 AND 200),
        is_done INTEGER NOT NULL DEFAULT 0 CHECK(is_done IN (0, 1)),
        position INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    )
"""

TASK_DEPENDENCIES_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS task_dependencies (
        id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
        depends_on_task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
        created_at TEXT NOT NULL,
        UNIQUE(task_id, depends_on_task_id)
    )
"""

MISSIONS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS missions (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL CHECK(length(trim(title)) BETWEEN 1 AND 200),
        description TEXT NOT NULL DEFAULT '',
        plan TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'planned',
        progress_percent INTEGER NOT NULL DEFAULT 0 CHECK(progress_percent BETWEEN 0 AND 100),
        created_at TEXT NOT NULL,
        completed_at TEXT,
        notes TEXT NOT NULL DEFAULT ''
    )
"""

PROJECT_MILESTONES_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS project_milestones (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        title TEXT NOT NULL CHECK(length(trim(title)) BETWEEN 1 AND 200),
        description TEXT NOT NULL DEFAULT '',
        due_date TEXT,
        completed_at TEXT,
        position INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    )
"""

CALENDAR_EVENTS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS calendar_events (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL CHECK(length(trim(title)) BETWEEN 1 AND 200),
        description TEXT NOT NULL DEFAULT '',
        starts_at TEXT NOT NULL,
        ends_at TEXT NOT NULL,
        timezone TEXT NOT NULL,
        priority TEXT NOT NULL DEFAULT 'normal'
            CHECK(priority IN ('low', 'normal', 'high', 'critical')),
        project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
        recurrence_kind TEXT NOT NULL DEFAULT 'none'
            CHECK(recurrence_kind IN ('none', 'daily', 'weekly', 'monthly')),
        recurrence_interval INTEGER NOT NULL DEFAULT 1
            CHECK(recurrence_interval >= 1),
        recurrence_until TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
"""

PLANNING_SETTINGS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS planning_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
"""

AI_PROPOSALS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS planning_ai_proposals (
        id TEXT PRIMARY KEY,
        operations_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        consumed_at TEXT
    )
"""

MISSION_LOGS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS mission_logs (
        id TEXT PRIMARY KEY,
        mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
        message TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
"""

MISSION_APPROVALS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS mission_approvals (
        id TEXT PRIMARY KEY,
        mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
        description TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending'
            CHECK(status IN ('pending', 'approved', 'rejected')),
        created_at TEXT NOT NULL,
        resolved_at TEXT
    )
"""


def default_planning_database_path() -> Path:
    override = os.getenv("JACK_PLANNING_DB_PATH", "").strip()
    if override:
        return Path(override).expanduser()

    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "J.A.C.K."
            / "tasks.sqlite3"
        )

    return Path.home() / ".local" / "share" / "J.A.C.K." / "tasks.sqlite3"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _today_iso() -> str:
    return date.today().isoformat()


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


class PlanningRepository:
    """SQLite-backed store per task, progetti, checklist, dipendenze e missioni."""

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = Path(
            database_path or default_planning_database_path()
        ).expanduser()

    def initialize(self) -> None:
        self.database_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version > SCHEMA_VERSION:
                raise RuntimeError(
                    "The local planning database is newer than this app."
                )
            if version == 0:
                self._ensure_schema(connection)
            elif version < SCHEMA_VERSION:
                self._migrate(connection, version)
            else:
                self._ensure_schema(connection)
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        self.database_path.chmod(0o600)

    def _ensure_schema(self, connection: sqlite3.Connection) -> None:
        connection.execute(TASKS_TABLE_SQL)
        connection.execute(PROJECTS_TABLE_SQL)
        connection.execute(CHECKLIST_ITEMS_TABLE_SQL)
        connection.execute(TASK_DEPENDENCIES_TABLE_SQL)
        connection.execute(MISSIONS_TABLE_SQL)
        connection.execute(PROJECT_MILESTONES_TABLE_SQL)
        connection.execute(CALENDAR_EVENTS_TABLE_SQL)
        connection.execute(PLANNING_SETTINGS_TABLE_SQL)
        connection.execute(AI_PROPOSALS_TABLE_SQL)
        connection.execute(MISSION_LOGS_TABLE_SQL)
        connection.execute(MISSION_APPROVALS_TABLE_SQL)
        mission_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(missions)").fetchall()
        }
        if "assigned_agents" not in mission_columns:
            connection.execute(
                "ALTER TABLE missions ADD COLUMN assigned_agents TEXT NOT NULL DEFAULT '[]'"
            )
        if "results" not in mission_columns:
            connection.execute(
                "ALTER TABLE missions ADD COLUMN results TEXT NOT NULL DEFAULT ''"
            )
        connection.execute(
            """
            INSERT OR IGNORE INTO planning_settings (key, value, updated_at)
            VALUES ('default_timezone', 'Europe/Rome', ?)
            """,
            (_now(),),
        )
        task_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(tasks)").fetchall()
        }
        if "recurrence_series_id" not in task_columns:
            connection.execute(
                "ALTER TABLE tasks ADD COLUMN recurrence_series_id TEXT"
            )
        connection.execute(
            """
            UPDATE tasks
            SET recurrence_series_id = id
            WHERE recurrence_kind != 'none' AND recurrence_series_id IS NULL
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_tasks_recurrence_series_due
            ON tasks(recurrence_series_id, due_date)
            WHERE recurrence_series_id IS NOT NULL AND due_date IS NOT NULL
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tasks_status
            ON tasks(status)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tasks_due_date
            ON tasks(due_date)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tasks_project_id
            ON tasks(project_id)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tasks_created_at
            ON tasks(created_at DESC)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_projects_status
            ON projects(status)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_checklist_items_task_id
            ON checklist_items(task_id, position)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_task_dependencies_task_id
            ON task_dependencies(task_id)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_task_dependencies_depends_on
            ON task_dependencies(depends_on_task_id)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_missions_status
            ON missions(status)
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_milestones_project ON project_milestones(project_id, position)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_calendar_events_start ON calendar_events(starts_at)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_calendar_events_project ON calendar_events(project_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_calendar_events_priority ON calendar_events(priority)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_ai_proposals_expiry ON planning_ai_proposals(expires_at)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_mission_logs_mission ON mission_logs(mission_id, created_at)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_mission_approvals_mission ON mission_approvals(mission_id, status)"
        )

    def _migrate(self, connection: sqlite3.Connection, from_version: int) -> None:
        if from_version < 1:
            raise RuntimeError(
                f"Non è supportata la migrazione dalla versione {from_version} del database di pianificazione."
            )
        self._ensure_schema(connection)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get_default_timezone(self) -> str:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT value FROM planning_settings WHERE key = 'default_timezone'"
            ).fetchone()
        return str(row["value"]) if row else "Europe/Rome"

    def set_default_timezone(self, timezone_name: str) -> str:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO planning_settings (key, value, updated_at)
                VALUES ('default_timezone', ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (timezone_name, _now()),
            )
        return timezone_name

    # ------------------------------------------------------------------ tasks

    def create_task(self, draft: dict[str, Any]) -> dict[str, Any]:
        now = _now()
        task_id = draft.get("id") or _new_id()
        tags = list(draft.get("tags") or [])
        recurrence_kind = str(
            draft.get("recurrence_kind", RecurrenceKind.NONE.value)
        )
        task = Task(
            id=task_id,
            title=str(draft["title"]),
            description=str(draft.get("description", "")),
            status=str(draft.get("status", TaskStatus.INBOX.value)),
            priority=str(draft.get("priority", TaskPriority.NORMAL.value)),
            category=str(draft.get("category", "")),
            tags=tags,
            created_at=draft.get("created_at", now),
            start_date=draft.get("start_date"),
            due_date=draft.get("due_date"),
            completed_at=draft.get("completed_at"),
            project_id=draft.get("project_id"),
            mission_id=draft.get("mission_id"),
            recurrence_kind=recurrence_kind,
            recurrence_interval=int(draft.get("recurrence_interval", 1)),
            recurrence_series_id=draft.get("recurrence_series_id")
            or (task_id if recurrence_kind != RecurrenceKind.NONE.value else None),
            ai_origin=bool(draft.get("ai_origin", False)),
            responsible_agent=draft.get("responsible_agent"),
            notes=str(draft.get("notes", "")),
            position=int(draft.get("position", 0)),
        )
        stored = task.to_dict()
        stored["tags"] = json.dumps(stored["tags"], ensure_ascii=False)
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO tasks (
                    id, title, description, status, priority, category, tags,
                    created_at, start_date, due_date, completed_at,
                    project_id, mission_id, recurrence_kind,
                    recurrence_interval, recurrence_series_id, ai_origin, responsible_agent,
                    notes, position
                ) VALUES (
                    :id, :title, :description, :status, :priority, :category,
                    :tags, :created_at, :start_date, :due_date,
                    :completed_at, :project_id, :mission_id,
                    :recurrence_kind, :recurrence_interval, :recurrence_series_id, :ai_origin,
                    :responsible_agent, :notes, :position
                )
                """,
                stored,
            )
        return self.get_task(task_id)

    def get_task(self, task_id: str) -> Optional[dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
        if row is None:
            return None
        return self._decode_task_row(dict(row), connection)

    def list_tasks(
        self,
        *,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        project_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        category: Optional[str] = None,
        overdue_only: bool = False,
        due_before: Optional[str] = None,
        due_after: Optional[str] = None,
        query: Optional[str] = None,
        tag: Optional[str] = None,
        sort: str = "created",
        descending: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: dict[str, Any] = {}

        if status is not None:
            clauses.append("status = :status")
            params["status"] = status
        if priority is not None:
            clauses.append("priority = :priority")
            params["priority"] = priority
        if project_id is not None:
            clauses.append("project_id = :project_id")
            params["project_id"] = project_id
        if mission_id is not None:
            clauses.append("mission_id = :mission_id")
            params["mission_id"] = mission_id
        if category is not None:
            clauses.append("category = :category")
            params["category"] = category
        if due_before is not None:
            clauses.append("due_date IS NOT NULL AND due_date <= :due_before")
            params["due_before"] = due_before
        if due_after is not None:
            clauses.append("due_date IS NOT NULL AND due_date >= :due_after")
            params["due_after"] = due_after
        if query is not None:
            clauses.append("(title LIKE :query OR description LIKE :query OR notes LIKE :query)")
            params["query"] = f"%{query}%"
        if tag is not None:
            clauses.append(
                "EXISTS (SELECT 1 FROM json_each(tasks.tags) WHERE json_each.value = :tag)"
            )
            params["tag"] = tag
        if overdue_only:
            clauses.append(
                "due_date IS NOT NULL AND due_date < :today "
                "AND status NOT IN ('completed', 'cancelled')"
            )
            params["today"] = _today_iso()

        sort_columns = {
            "created": "created_at",
            "due_date": "due_date",
            "priority": "CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END",
            "title": "title COLLATE NOCASE",
        }
        order_by = sort_columns.get(sort, sort_columns["created"])
        direction = "DESC" if descending else "ASC"
        sql = "SELECT * FROM tasks"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        if sort == "created":
            direction = "DESC" if not descending else "ASC"
        sql += f" ORDER BY {order_by} {direction}, position ASC, title COLLATE NOCASE ASC"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        if offset is not None:
            sql += f" OFFSET {int(offset)}"

        with self._connection() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [
            self._decode_task_row(dict(row), connection) for row in rows
        ]

    def update_task(self, task_id: str, patch: dict[str, Any]) -> Optional[dict[str, Any]]:
        existing = self.get_task(task_id)
        if existing is None:
            return None

        allowed = {
            "title", "description", "status", "priority", "category", "tags",
            "start_date", "due_date", "completed_at", "project_id",
            "mission_id", "recurrence_kind", "recurrence_interval",
            "ai_origin", "responsible_agent", "notes", "position",
        }
        updates: dict[str, Any] = {k: v for k, v in patch.items() if k in allowed}
        if not updates:
            return existing

        if "tags" in updates:
            updates["tags"] = json.dumps(list(updates["tags"] or []), ensure_ascii=False)
        if "recurrence_kind" in updates:
            if updates["recurrence_kind"] == RecurrenceKind.NONE.value:
                updates["recurrence_series_id"] = None
            elif existing.get("recurrence_series_id") is None:
                updates["recurrence_series_id"] = task_id

        with self._connection() as connection:
            set_clause = ", ".join(f"{k} = :{k}" for k in updates)
            updates["id"] = task_id
            connection.execute(
                f"UPDATE tasks SET {set_clause} WHERE id = :id", updates
            )
        return self.get_task(task_id)

    def has_recurrence_instance(self, series_id: str, due_date: str) -> bool:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT 1 FROM tasks
                WHERE recurrence_series_id = ? AND due_date = ?
                LIMIT 1
                """,
                (series_id, due_date),
            ).fetchone()
        return row is not None

    def delete_task(self, task_id: str) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM tasks WHERE id = ?", (task_id,)
            )
        return cursor.rowcount > 0

    def complete_task(self, task_id: str) -> dict[str, Any]:
        """Segna un task come completato se i prerequisiti sono soddisfatti."""
        task = self.get_task(task_id)
        if task is None:
            raise KeyError(f"Task {task_id} non trovato.")
        if task["status"] == TaskStatus.COMPLETED.value:
            return task

        # Controllo dipendenze: nessun prerequisito non completato.
        dependencies = self.list_dependencies_for_task(task_id)
        for dep in dependencies:
            prerequisite = self.get_task(dep["depends_on_task_id"])
            if prerequisite is None or prerequisite["status"] != TaskStatus.COMPLETED.value:
                raise ValueError(
                    "Impossibile completare: il prerequisito "
                    f"“{prerequisite['title'] if prerequisite else 'sconosciuto'}” "
                    "non è stato completato."
                )

        now = _now()
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE tasks
                SET status = 'completed', completed_at = ?
                WHERE id = ?
                """,
                (now, task_id),
            )
        return self.get_task(task_id)

    def reopen_task(self, task_id: str) -> Optional[dict[str, Any]]:
        task = self.get_task(task_id)
        if task is None:
            return None
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE tasks
                SET status = 'todo', completed_at = NULL
                WHERE id = ?
                """,
                (task_id,),
            )
        return self.get_task(task_id)

    # --------------------------------------------------------------- checklist

    def add_checklist_item(
        self, task_id: str, title: str, position: int = 0
    ) -> dict[str, Any]:
        if self.get_task(task_id) is None:
            raise KeyError(f"Task {task_id} non trovato.")
        item = ChecklistItem(
            id=_new_id(),
            task_id=task_id,
            title=title,
            position=position,
        )
        stored = item.to_dict()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO checklist_items (
                    id, task_id, title, is_done, position, created_at
                ) VALUES (
                    :id, :task_id, :title, :is_done, :position, :created_at
                )
                """,
                stored,
            )
        return stored

    def update_checklist_item(
        self, item_id: str, patch: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        allowed = {"title", "is_done", "position"}
        updates = {k: v for k, v in patch.items() if k in allowed}
        if not updates:
            return self.get_checklist_item(item_id)
        with self._connection() as connection:
            set_clause = ", ".join(f"{k} = :{k}" for k in updates)
            updates["id"] = item_id
            cursor = connection.execute(
                f"UPDATE checklist_items SET {set_clause} WHERE id = :id",
                updates,
            )
            if cursor.rowcount == 0:
                return None
        return self.get_checklist_item(item_id)

    def get_checklist_item(self, item_id: str) -> Optional[dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM checklist_items WHERE id = ?", (item_id,)
            ).fetchone()
        return dict(row) if row is not None else None

    def list_checklist_items(
        self, task_id: str
    ) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM checklist_items
                WHERE task_id = ?
                ORDER BY position ASC, created_at ASC
                """,
                (task_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_checklist_item(self, item_id: str) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM checklist_items WHERE id = ?", (item_id,)
            )
        return cursor.rowcount > 0

    # ------------------------------------------------------------- dependencies

    def add_dependency(
        self, task_id: str, depends_on_task_id: str
    ) -> dict[str, Any]:
        if task_id == depends_on_task_id:
            raise ValueError("Un task non può dipendere da sé stesso.")
        if self.get_task(task_id) is None or self.get_task(depends_on_task_id) is None:
            raise KeyError("Uno dei task specificati non esiste.")
        # Controllo ciclo: depends_on_task_id non deve dipendere (direttamente o indirettamente) da task_id.
        if self._would_create_cycle(task_id, depends_on_task_id):
            raise ValueError("La dipendenza creerebbe un ciclo tra attività.")
        dependency = TaskDependency(
            id=_new_id(),
            task_id=task_id,
            depends_on_task_id=depends_on_task_id,
        )
        stored = dependency.to_dict()
        with self._connection() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO task_dependencies (
                        id, task_id, depends_on_task_id, created_at
                    ) VALUES (
                        :id, :task_id, :depends_on_task_id, :created_at
                    )
                    """,
                    stored,
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("La dipendenza già esiste.") from exc
        return stored

    def remove_dependency(self, dependency_id: str) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM task_dependencies WHERE id = ?", (dependency_id,)
            )
        return cursor.rowcount > 0

    def list_dependencies_for_task(
        self, task_id: str
    ) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM task_dependencies
                WHERE task_id = ?
                ORDER BY created_at ASC
                """,
                (task_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_dependents_of_task(
        self, task_id: str
    ) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM task_dependencies
                WHERE depends_on_task_id = ?
                ORDER BY created_at ASC
                """,
                (task_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def _would_create_cycle(self, task_id: str, depends_on_task_id: str) -> bool:
        # DFS: partendo da depends_on_task_id, segui le sue dipendenze;
        # se raggiungiamo task_id => ciclo.
        visited: set[str] = set()
        stack = [depends_on_task_id]
        while stack:
            current = stack.pop()
            if current == task_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            for dep in self.list_dependencies_for_task(current):
                stack.append(dep["depends_on_task_id"])
        return False

    # ----------------------------------------------------------------- projects

    def create_project(self, draft: dict[str, Any]) -> dict[str, Any]:
        now = _now()
        project_id = draft.get("id") or _new_id()
        project = Project(
            id=project_id,
            name=str(draft["name"]),
            description=str(draft.get("description", "")),
            goal=str(draft.get("goal", "")),
            status=str(draft.get("status", "active")),
            priority=str(draft.get("priority", TaskPriority.NORMAL.value)),
            start_date=draft.get("start_date"),
            due_date=draft.get("due_date"),
            notes=str(draft.get("notes", "")),
            created_at=draft.get("created_at", now),
            archived_at=draft.get("archived_at"),
        )
        stored = project.to_dict()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO projects (
                    id, name, description, goal, status, priority,
                    start_date, due_date, notes, created_at, archived_at
                ) VALUES (
                    :id, :name, :description, :goal, :status, :priority,
                    :start_date, :due_date, :notes, :created_at, :archived_at
                )
                """,
                stored,
            )
        return self.get_project(project_id)

    def get_project(self, project_id: str) -> Optional[dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
        if row is None:
            return None
        project = Project.from_dict(dict(row))
        tasks = self.list_tasks(project_id=project_id)
        project.task_ids = [t["id"] for t in tasks]
        project.open_task_count = sum(
            1 for t in tasks if t["status"] != TaskStatus.COMPLETED.value
        )
        project.completed_task_count = sum(
            1 for t in tasks if t["status"] == TaskStatus.COMPLETED.value
        )
        project.open_task_count = sum(
            1
            for t in tasks
            if t["status"] not in {
                TaskStatus.COMPLETED.value,
                TaskStatus.CANCELLED.value,
            }
        )
        total = sum(
            1 for t in tasks if t["status"] != TaskStatus.CANCELLED.value
        )
        project.completion_percent = (
            int(round(project.completed_task_count * 100 / total)) if total else 0
        )
        project.milestones = self.list_milestones(project_id)
        return project.to_dict_with_stats()

    def list_projects(
        self, *, include_archived: bool = False, query: Optional[str] = None
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: dict[str, Any] = {}
        if not include_archived:
            clauses.append("(status != 'archived' AND archived_at IS NULL)")
        if query is not None:
            clauses.append("(name LIKE :query OR description LIKE :query OR goal LIKE :query)")
            params["query"] = f"%{query}%"
        sql = "SELECT * FROM projects"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at DESC, name ASC"
        with self._connection() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [self.get_project(dict(row)["id"]) for row in rows]  # type: ignore[arg-type]

    def update_project(self, project_id: str, patch: dict[str, Any]) -> Optional[dict[str, Any]]:
        existing = self.get_project(project_id)
        if existing is None:
            return None
        allowed = {
            "name", "description", "goal", "status", "priority",
            "start_date", "due_date", "notes", "archived_at",
        }
        updates = {k: v for k, v in patch.items() if k in allowed}
        if not updates:
            return existing
        with self._connection() as connection:
            set_clause = ", ".join(f"{k} = :{k}" for k in updates)
            updates["id"] = project_id
            connection.execute(
                f"UPDATE projects SET {set_clause} WHERE id = :id", updates
            )
        return self.get_project(project_id)

    def archive_project(self, project_id: str) -> Optional[dict[str, Any]]:
        project = self.get_project(project_id)
        if project is None:
            return None
        now = _now()
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE projects
                SET status = 'archived', archived_at = ?
                WHERE id = ?
                """,
                (now, project_id),
            )
        return self.get_project(project_id)

    def delete_project(self, project_id: str) -> bool:
        with self._connection() as connection:
            connection.execute(
                "UPDATE tasks SET project_id = NULL WHERE project_id = ?",
                (project_id,),
            )
            cursor = connection.execute(
                "DELETE FROM projects WHERE id = ?", (project_id,)
            )
        return cursor.rowcount > 0

    # ---------------------------------------------------------- milestones

    def create_milestone(
        self, project_id: str, draft: dict[str, Any]
    ) -> dict[str, Any]:
        if self.get_project(project_id) is None:
            raise KeyError(f"Progetto {project_id} non trovato.")
        stored = {
            "id": draft.get("id") or _new_id(),
            "project_id": project_id,
            "title": str(draft["title"]).strip(),
            "description": str(draft.get("description", "")),
            "due_date": draft.get("due_date"),
            "completed_at": draft.get("completed_at"),
            "position": int(draft.get("position", 0)),
            "created_at": draft.get("created_at", _now()),
        }
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO project_milestones (
                    id, project_id, title, description, due_date, completed_at,
                    position, created_at
                ) VALUES (
                    :id, :project_id, :title, :description, :due_date,
                    :completed_at, :position, :created_at
                )
                """,
                stored,
            )
        return stored

    def list_milestones(self, project_id: str) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM project_milestones
                WHERE project_id = ?
                ORDER BY position ASC, due_date ASC, created_at ASC
                """,
                (project_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def update_milestone(
        self, milestone_id: str, patch: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        allowed = {"title", "description", "due_date", "completed_at", "position"}
        updates = {key: value for key, value in patch.items() if key in allowed}
        with self._connection() as connection:
            if updates:
                updates["id"] = milestone_id
                set_clause = ", ".join(f"{key} = :{key}" for key in updates)
                cursor = connection.execute(
                    f"UPDATE project_milestones SET {set_clause} WHERE id = :id",
                    updates,
                )
                if cursor.rowcount == 0:
                    return None
            row = connection.execute(
                "SELECT * FROM project_milestones WHERE id = ?", (milestone_id,)
            ).fetchone()
        return dict(row) if row is not None else None

    def delete_milestone(self, milestone_id: str) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM project_milestones WHERE id = ?", (milestone_id,)
            )
        return cursor.rowcount > 0

    # ---------------------------------------------------------- calendar events

    def create_event(self, draft: dict[str, Any]) -> dict[str, Any]:
        now = _now()
        stored = {
            "id": draft.get("id") or _new_id(),
            "title": str(draft["title"]).strip(),
            "description": str(draft.get("description", "")),
            "starts_at": str(draft["starts_at"]),
            "ends_at": str(draft["ends_at"]),
            "timezone": str(draft["timezone"]),
            "priority": str(draft.get("priority", TaskPriority.NORMAL.value)),
            "project_id": draft.get("project_id"),
            "recurrence_kind": str(
                draft.get("recurrence_kind", RecurrenceKind.NONE.value)
            ),
            "recurrence_interval": int(draft.get("recurrence_interval", 1)),
            "recurrence_until": draft.get("recurrence_until"),
            "created_at": draft.get("created_at", now),
            "updated_at": draft.get("updated_at", now),
        }
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO calendar_events (
                    id, title, description, starts_at, ends_at, timezone,
                    priority, project_id, recurrence_kind, recurrence_interval,
                    recurrence_until, created_at, updated_at
                ) VALUES (
                    :id, :title, :description, :starts_at, :ends_at, :timezone,
                    :priority, :project_id, :recurrence_kind,
                    :recurrence_interval, :recurrence_until, :created_at,
                    :updated_at
                )
                """,
                stored,
            )
        return self.get_event(stored["id"])

    def get_event(self, event_id: str) -> Optional[dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM calendar_events WHERE id = ?", (event_id,)
            ).fetchone()
        return dict(row) if row is not None else None

    def list_events(
        self,
        *,
        starts_at: Optional[str] = None,
        ends_at: Optional[str] = None,
        project_id: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: dict[str, Any] = {}
        if starts_at is not None:
            clauses.append("ends_at >= :starts_at")
            params["starts_at"] = starts_at
        if ends_at is not None:
            clauses.append("starts_at < :ends_at")
            params["ends_at"] = ends_at
        if project_id is not None:
            clauses.append("project_id = :project_id")
            params["project_id"] = project_id
        if priority is not None:
            clauses.append("priority = :priority")
            params["priority"] = priority
        sql = "SELECT * FROM calendar_events"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY starts_at ASC, title ASC"
        with self._connection() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def update_event(
        self, event_id: str, patch: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        allowed = {
            "title", "description", "starts_at", "ends_at", "timezone",
            "priority", "project_id", "recurrence_kind", "recurrence_interval",
            "recurrence_until",
        }
        updates = {key: value for key, value in patch.items() if key in allowed}
        if updates:
            updates["updated_at"] = _now()
            updates["id"] = event_id
            with self._connection() as connection:
                set_clause = ", ".join(f"{key} = :{key}" for key in updates)
                cursor = connection.execute(
                    f"UPDATE calendar_events SET {set_clause} WHERE id = :id",
                    updates,
                )
                if cursor.rowcount == 0:
                    return None
        return self.get_event(event_id)

    def delete_event(self, event_id: str) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM calendar_events WHERE id = ?", (event_id,)
            )
        return cursor.rowcount > 0

    # ----------------------------------------------------------- AI proposals

    def create_ai_proposal(
        self, operations: list[dict[str, Any]], *, expires_at: str
    ) -> str:
        proposal_id = _new_id()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO planning_ai_proposals (
                    id, operations_json, created_at, expires_at
                ) VALUES (?, ?, ?, ?)
                """,
                (proposal_id, json.dumps(operations), _now(), expires_at),
            )
        return proposal_id

    def consume_ai_proposal(
        self, proposal_id: str
    ) -> Optional[list[dict[str, Any]]]:
        now = _now()
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT operations_json FROM planning_ai_proposals
                WHERE id = ? AND consumed_at IS NULL AND expires_at > ?
                """,
                (proposal_id, now),
            ).fetchone()
            if row is None:
                return None
            cursor = connection.execute(
                """
                UPDATE planning_ai_proposals SET consumed_at = ?
                WHERE id = ? AND consumed_at IS NULL AND expires_at > ?
                """,
                (now, proposal_id, now),
            )
            if cursor.rowcount != 1:
                return None
            operations = json.loads(row["operations_json"])
        return operations if isinstance(operations, list) else None

    # ------------------------------------------------------------------ missions

    def create_mission(self, draft: dict[str, Any]) -> dict[str, Any]:
        now = _now()
        mission_id = draft.get("id") or _new_id()
        mission = Mission(
            id=mission_id,
            title=str(draft["title"]),
            description=str(draft.get("description", "")),
            plan=str(draft.get("plan", "")),
            status=str(draft.get("status", "planned")),
            progress_percent=int(draft.get("progress_percent", 0)),
            created_at=draft.get("created_at", now),
            completed_at=draft.get("completed_at"),
            notes=str(draft.get("notes", "")),
            assigned_agents=list(draft.get("assigned_agents") or []),
            results=str(draft.get("results", "")),
        )
        stored = mission.to_dict()
        stored["assigned_agents"] = json.dumps(
            stored["assigned_agents"], ensure_ascii=False
        )
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO missions (
                    id, title, description, plan, status,
                    progress_percent, created_at, completed_at, notes,
                    assigned_agents, results
                ) VALUES (
                    :id, :title, :description, :plan, :status,
                    :progress_percent, :created_at, :completed_at, :notes,
                    :assigned_agents, :results
                )
                """,
                stored,
            )
        return self.get_mission(mission_id)

    def get_mission(self, mission_id: str) -> Optional[dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM missions WHERE id = ?", (mission_id,)
            ).fetchone()
        if row is None:
            return None
        mission = Mission.from_dict(dict(row))
        tasks = self.list_tasks(mission_id=mission_id)
        mission.task_ids = [t["id"] for t in tasks]
        active_tasks = [
            task for task in tasks if task["status"] != TaskStatus.CANCELLED.value
        ]
        completed_count = sum(
            1 for task in active_tasks
            if task["status"] == TaskStatus.COMPLETED.value
        )
        mission.progress_percent = (
            round(100 * completed_count / len(active_tasks)) if active_tasks else 0
        )
        with self._connection() as connection:
            mission.logs = [
                dict(log)
                for log in connection.execute(
                    "SELECT * FROM mission_logs WHERE mission_id = ? ORDER BY created_at",
                    (mission_id,),
                ).fetchall()
            ]
            mission.approvals = [
                dict(approval)
                for approval in connection.execute(
                    "SELECT * FROM mission_approvals WHERE mission_id = ? ORDER BY created_at",
                    (mission_id,),
                ).fetchall()
            ]
        return mission.to_dict_with_stats()

    def list_missions(self, *, status: Optional[str] = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        sql = "SELECT * FROM missions"
        if status is not None:
            sql += " WHERE status = :status"
            params["status"] = status
        sql += " ORDER BY created_at DESC, title ASC"
        with self._connection() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [self.get_mission(dict(row)["id"]) for row in rows]  # type: ignore[arg-type]

    def update_mission(self, mission_id: str, patch: dict[str, Any]) -> Optional[dict[str, Any]]:
        existing = self.get_mission(mission_id)
        if existing is None:
            return None
        allowed = {
            "title", "description", "plan", "status", "notes", "results",
            "assigned_agents",
        }
        updates = {k: v for k, v in patch.items() if k in allowed}
        if not updates:
            return existing
        if "assigned_agents" in updates:
            updates["assigned_agents"] = json.dumps(
                list(updates["assigned_agents"] or []), ensure_ascii=False
            )
        with self._connection() as connection:
            set_clause = ", ".join(f"{k} = :{k}" for k in updates)
            updates["id"] = mission_id
            connection.execute(
                f"UPDATE missions SET {set_clause} WHERE id = :id", updates
            )
        return self.get_mission(mission_id)

    def add_mission_log(self, mission_id: str, message: str) -> dict[str, Any]:
        stored = {
            "id": _new_id(),
            "mission_id": mission_id,
            "message": message,
            "created_at": _now(),
        }
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO mission_logs (id, mission_id, message, created_at)
                VALUES (:id, :mission_id, :message, :created_at)
                """,
                stored,
            )
        return stored

    def create_mission_approval(
        self, mission_id: str, description: str
    ) -> dict[str, Any]:
        stored = {
            "id": _new_id(),
            "mission_id": mission_id,
            "description": description,
            "status": "pending",
            "created_at": _now(),
            "resolved_at": None,
        }
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO mission_approvals (
                    id, mission_id, description, status, created_at, resolved_at
                ) VALUES (
                    :id, :mission_id, :description, :status, :created_at,
                    :resolved_at
                )
                """,
                stored,
            )
        return stored

    def update_mission_approval(
        self, approval_id: str, status: str
    ) -> Optional[dict[str, Any]]:
        resolved_at = _now() if status != "pending" else None
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE mission_approvals
                SET status = ?, resolved_at = ?
                WHERE id = ?
                """,
                (status, resolved_at, approval_id),
            )
            if cursor.rowcount == 0:
                return None
            row = connection.execute(
                "SELECT * FROM mission_approvals WHERE id = ?", (approval_id,)
            ).fetchone()
        return dict(row) if row is not None else None

    def delete_mission(self, mission_id: str) -> bool:
        with self._connection() as connection:
            connection.execute(
                "UPDATE tasks SET mission_id = NULL WHERE mission_id = ?",
                (mission_id,),
            )
            cursor = connection.execute(
                "DELETE FROM missions WHERE id = ?", (mission_id,)
            )
        return cursor.rowcount > 0

    # ---------------------------------------------------------------- decoding

    def _decode_task_row(
        self, row: dict[str, Any], connection: sqlite3.Connection
    ) -> dict[str, Any]:
        try:
            tags = json.loads(str(row.get("tags") or "[]"))
            if not isinstance(tags, list):
                tags = []
        except (json.JSONDecodeError, TypeError):
            tags = []
        task = Task(
            id=row["id"],
            title=row["title"],
            description=row.get("description", ""),
            status=row.get("status", TaskStatus.INBOX.value),
            priority=row.get("priority", TaskPriority.NORMAL.value),
            category=row.get("category", ""),
            tags=tags,
            created_at=row.get("created_at", _now()),
            start_date=row.get("start_date"),
            due_date=row.get("due_date"),
            completed_at=row.get("completed_at"),
            project_id=row.get("project_id"),
            mission_id=row.get("mission_id"),
            recurrence_kind=row.get("recurrence_kind", RecurrenceKind.NONE.value),
            recurrence_interval=int(row.get("recurrence_interval", 1)),
            recurrence_series_id=row.get("recurrence_series_id"),
            ai_origin=bool(row.get("ai_origin", 0)),
            responsible_agent=row.get("responsible_agent"),
            notes=row.get("notes", ""),
            position=int(row.get("position", 0)),
        )
        task.checklist = [
            ChecklistItem.from_dict(i) for i in self.list_checklist_items(task.id)
        ]
        task.dependencies = [
            TaskDependency.from_dict(d) for d in self.list_dependencies_for_task(task.id)
        ]
        task.dependents = [
            d["task_id"] for d in self.list_dependents_of_task(task.id)
        ]
        return task.to_dict(include_checklist=True)
