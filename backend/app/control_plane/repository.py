from __future__ import annotations

import json
import os
import sqlite3
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.control_plane.models import IdentityKind

SCHEMA_VERSION = 1
_AUDIT_ACTOR_KIND = IdentityKind.SERVICE.value
_AUDIT_ACTOR_ID = "control-plane-api"

IDENTITIES_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS control_plane_identities (
        kind TEXT NOT NULL CHECK(kind IN ('user', 'agent', 'service', 'tool', 'node')),
        id TEXT NOT NULL,
        display_name TEXT NOT NULL CHECK(length(trim(display_name)) BETWEEN 1 AND 200),
        declared_at TEXT NOT NULL,
        PRIMARY KEY(kind, id)
    )
"""

CAPABILITIES_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS control_plane_capabilities (
        id TEXT PRIMARY KEY,
        owner_kind TEXT NOT NULL,
        owner_id TEXT NOT NULL,
        description TEXT NOT NULL,
        resource TEXT NOT NULL,
        operations_json TEXT NOT NULL,
        scope_json TEXT NOT NULL,
        risk_level TEXT NOT NULL CHECK(risk_level IN ('low', 'normal', 'high', 'critical')),
        approval_required INTEGER NOT NULL CHECK(approval_required IN (0, 1)),
        declared_at TEXT NOT NULL,
        FOREIGN KEY(owner_kind, owner_id)
            REFERENCES control_plane_identities(kind, id)
    )
"""

AGENT_ASSIGNMENTS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS control_plane_agent_assignments (
        id TEXT PRIMARY KEY,
        agent_kind TEXT NOT NULL CHECK(agent_kind IN ('user', 'agent', 'service', 'tool', 'node')),
        agent_id TEXT NOT NULL,
        mission_id TEXT NOT NULL,
        assigned_at TEXT NOT NULL,
        assigned_by_kind TEXT NOT NULL CHECK(assigned_by_kind IN ('user', 'agent', 'service', 'tool', 'node')),
        assigned_by_id TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('active', 'revoked')),
        FOREIGN KEY(agent_kind, agent_id)
            REFERENCES control_plane_identities(kind, id)
    )
"""

BACKGROUND_TASKS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS background_tasks (
        id TEXT PRIMARY KEY,
        task_type TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('pending', 'running', 'completed', 'cancelled', 'failed')),
        created_at TEXT NOT NULL,
        started_at TEXT,
        completed_at TEXT,
        result_json TEXT,
        error_json TEXT,
        timeout_seconds INTEGER NOT NULL DEFAULT 300,
        max_retries INTEGER NOT NULL DEFAULT 3,
        retry_count INTEGER NOT NULL DEFAULT 0
    )
"""

EVOLUTION_PATCH_PROPOSALS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS evolution_patch_proposals (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        target_file TEXT NOT NULL,
        patch_content TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('pending', 'approved', 'rejected')),
        proposed_by_kind TEXT NOT NULL CHECK(proposed_by_kind IN ('user', 'agent', 'service', 'tool', 'node')),
        proposed_by_id TEXT NOT NULL,
        proposed_at TEXT NOT NULL,
        reviewed_by_kind TEXT CHECK(reviewed_by_kind IN ('user', 'agent', 'service', 'tool', 'node')),
        reviewed_by_id TEXT,
        reviewed_at TEXT,
        approval_reason TEXT,
        FOREIGN KEY(proposed_by_kind, proposed_by_id)
            REFERENCES control_plane_identities(kind, id)
    )
"""

GENERAL_PREFERENCES_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS general_preferences (
        key TEXT PRIMARY KEY,
        value_json TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
"""

AUDIT_EVENTS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS control_plane_audit_events (
        id TEXT PRIMARY KEY,
        occurred_at TEXT NOT NULL,
        actor_kind TEXT NOT NULL CHECK(actor_kind IN (
            'user', 'agent', 'service', 'tool', 'node'
        )),
        actor_id TEXT NOT NULL,
        action TEXT NOT NULL,
        subject_kind TEXT NOT NULL CHECK(subject_kind IN (
            'user', 'agent', 'service', 'tool', 'node'
        )),
        subject_id TEXT NOT NULL,
        outcome TEXT NOT NULL CHECK(outcome = 'recorded'),
        details_json TEXT NOT NULL,
        FOREIGN KEY(actor_kind, actor_id)
            REFERENCES control_plane_identities(kind, id),
        FOREIGN KEY(subject_kind, subject_id)
            REFERENCES control_plane_identities(kind, id)
    )
"""


def default_control_plane_database_path() -> Path:
    override = os.getenv("JACK_CONTROL_PLANE_DB_PATH", "").strip()
    if override:
        return Path(override).expanduser()
    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "J.A.C.K."
            / "control-plane.sqlite3"
        )
    return Path.home() / ".local" / "share" / "J.A.C.K." / "control-plane.sqlite3"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class DuplicateDeclarationError(ValueError):
    pass


class IdentityNotFoundError(KeyError):
    pass


class ControlPlaneRepository:
    """Separate local store for declarations and append-only control-plane audit."""

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = Path(
            database_path or default_control_plane_database_path()
        ).expanduser()

    def initialize(self) -> None:
        self.database_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with self._connection() as connection:
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version > SCHEMA_VERSION:
                raise RuntimeError(
                    "The local Control Plane database is newer than this app."
                )
            self._ensure_schema(connection)
            connection.execute(
                """
                INSERT OR IGNORE INTO control_plane_identities
                    (kind, id, display_name, declared_at)
                VALUES ('service', ?, 'Control Plane API', ?)
                """,
                (_AUDIT_ACTOR_ID, _now()),
            )
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        self.database_path.chmod(0o600)

    @staticmethod
    def _ensure_schema(connection: sqlite3.Connection) -> None:
        connection.execute(IDENTITIES_TABLE_SQL)
        connection.execute(CAPABILITIES_TABLE_SQL)
        connection.execute(AGENT_ASSIGNMENTS_TABLE_SQL)
        connection.execute(BACKGROUND_TASKS_TABLE_SQL)
        connection.execute(EVOLUTION_PATCH_PROPOSALS_TABLE_SQL)
        connection.execute(GENERAL_PREFERENCES_TABLE_SQL)
        connection.execute(AUDIT_EVENTS_TABLE_SQL)
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_control_plane_capabilities_owner
            ON control_plane_capabilities(owner_kind, owner_id, declared_at)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_control_plane_audit_occurred
            ON control_plane_audit_events(occurred_at DESC)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_control_plane_audit_subject
            ON control_plane_audit_events(subject_kind, subject_id, occurred_at DESC)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_control_plane_agent_assignments_agent
            ON control_plane_agent_assignments(agent_kind, agent_id, status)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_control_plane_agent_assignments_mission
            ON control_plane_agent_assignments(mission_id, status)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_background_tasks_status
            ON background_tasks(status, created_at)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_background_tasks_type
            ON background_tasks(task_type, status)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_evolution_patch_proposals_status
            ON evolution_patch_proposals(status, proposed_at)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_evolution_patch_proposals_proposer
            ON evolution_patch_proposals(proposed_by_kind, proposed_by_id)
            """
        )
        connection.execute(
            """
            CREATE TRIGGER IF NOT EXISTS control_plane_audit_no_update
            BEFORE UPDATE ON control_plane_audit_events
            BEGIN
                SELECT RAISE(ABORT, 'Control Plane audit events are immutable.');
            END
            """
        )
        connection.execute(
            """
            CREATE TRIGGER IF NOT EXISTS control_plane_audit_no_delete
            BEFORE DELETE ON control_plane_audit_events
            BEGIN
                SELECT RAISE(ABORT, 'Control Plane audit events are immutable.');
            END
            """
        )

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

    def declare_identity(self, declaration: dict[str, Any]) -> dict[str, Any]:
        occurred_at = _now()
        with self._connection() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO control_plane_identities
                        (kind, id, display_name, declared_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        declaration["kind"],
                        declaration["id"],
                        declaration["display_name"],
                        occurred_at,
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise DuplicateDeclarationError(
                    "Identity declaration already exists."
                ) from error
            self._append_audit(
                connection,
                action="identity.declared",
                subject_kind=declaration["kind"],
                subject_id=declaration["id"],
                details={"display_name": declaration["display_name"]},
                occurred_at=occurred_at,
            )
        return self.get_identity(declaration["kind"], declaration["id"])

    def get_identity(self, kind: str, identity_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT kind, id, display_name, declared_at
                FROM control_plane_identities WHERE kind = ? AND id = ?
                """,
                (kind, identity_id),
            ).fetchone()
        return dict(row) if row is not None else None

    def list_identities(
        self, *, kind: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[dict[str, Any]]:
        with self._connection() as connection:
            if kind is None:
                rows = connection.execute(
                    """
                    SELECT kind, id, display_name, declared_at
                    FROM control_plane_identities
                    ORDER BY kind, id LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT kind, id, display_name, declared_at
                    FROM control_plane_identities WHERE kind = ?
                    ORDER BY id LIMIT ? OFFSET ?
                    """,
                    (kind, limit, offset),
                ).fetchall()
        return [dict(row) for row in rows]

    def declare_capability(self, declaration: dict[str, Any]) -> dict[str, Any]:
        owner = declaration["owner"]
        occurred_at = _now()
        with self._connection() as connection:
            exists = connection.execute(
                """
                SELECT 1 FROM control_plane_identities WHERE kind = ? AND id = ?
                """,
                (owner["kind"], owner["id"]),
            ).fetchone()
            if exists is None:
                raise IdentityNotFoundError(
                    f"Declared owner identity {owner['kind']}:{owner['id']} was not found."
                )
            try:
                connection.execute(
                    """
                    INSERT INTO control_plane_capabilities (
                        id, owner_kind, owner_id, description, resource,
                        operations_json, scope_json, risk_level,
                        approval_required, declared_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        declaration["id"],
                        owner["kind"],
                        owner["id"],
                        declaration["description"],
                        declaration["resource"],
                        _json(declaration["operations"]),
                        _json(declaration["scope"]),
                        declaration["risk_level"],
                        int(declaration["approval_required"]),
                        occurred_at,
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise DuplicateDeclarationError(
                    "Capability declaration already exists."
                ) from error
            self._append_audit(
                connection,
                action="capability.declared",
                subject_kind=owner["kind"],
                subject_id=owner["id"],
                details={
                    "capability_id": declaration["id"],
                    "resource": declaration["resource"],
                    "operations": declaration["operations"],
                    "risk_level": declaration["risk_level"],
                    "approval_required": declaration["approval_required"],
                },
                occurred_at=occurred_at,
            )
        return self.get_capability(declaration["id"])

    def get_capability(self, capability_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT id, owner_kind, owner_id, description, resource,
                       operations_json, scope_json, risk_level,
                       approval_required, declared_at
                FROM control_plane_capabilities WHERE id = ?
                """,
                (capability_id,),
            ).fetchone()
        return self._decode_capability(row) if row is not None else None

    def list_capabilities(
        self,
        *,
        owner_kind: str | None = None,
        owner_id: str | None = None,
        resource: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if owner_kind is not None:
            clauses.append("owner_kind = ?")
            params.append(owner_kind)
        if owner_id is not None:
            clauses.append("owner_id = ?")
            params.append(owner_id)
        if resource is not None:
            clauses.append("resource = ?")
            params.append(resource)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connection() as connection:
            rows = connection.execute(
                f"""
                SELECT id, owner_kind, owner_id, description, resource,
                       operations_json, scope_json, risk_level,
                       approval_required, declared_at
                FROM control_plane_capabilities {where}
                ORDER BY declared_at DESC, id LIMIT ? OFFSET ?
                """,
                (*params, limit, offset),
            ).fetchall()
        return [self._decode_capability(row) for row in rows]

    def list_audit_events(
        self,
        *,
        subject_kind: str | None = None,
        subject_id: str | None = None,
        action: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if subject_kind is not None:
            clauses.append("subject_kind = ?")
            params.append(subject_kind)
        if subject_id is not None:
            clauses.append("subject_id = ?")
            params.append(subject_id)
        if action is not None:
            clauses.append("action = ?")
            params.append(action)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connection() as connection:
            rows = connection.execute(
                f"""
                SELECT id, occurred_at, actor_kind, actor_id, action,
                       subject_kind, subject_id, outcome, details_json
                FROM control_plane_audit_events {where}
                ORDER BY occurred_at DESC, rowid DESC LIMIT ? OFFSET ?
                """,
                (*params, limit, offset),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "occurred_at": row["occurred_at"],
                "actor": {"kind": row["actor_kind"], "id": row["actor_id"]},
                "action": row["action"],
                "subject": {"kind": row["subject_kind"], "id": row["subject_id"]},
                "outcome": row["outcome"],
                "details": json.loads(row["details_json"]),
            }
            for row in rows
        ]

    @staticmethod
    def _decode_capability(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "owner": {"kind": row["owner_kind"], "id": row["owner_id"]},
            "description": row["description"],
            "resource": row["resource"],
            "operations": json.loads(row["operations_json"]),
            "scope": json.loads(row["scope_json"]),
            "risk_level": row["risk_level"],
            "approval_required": bool(row["approval_required"]),
            "declared_at": row["declared_at"],
        }

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
        """Assegna un agente operativo a una missione.

        Crea un registro di assegnazione attiva. Se esiste già un'assegnazione
        attiva per la stessa coppia agente/missione, solleva errore.
        """
        occurred_at = _now()
        assignment_id = str(uuid.uuid4())
        with self._connection() as connection:
            # Verifica che l'identità agente esista.
            agent_exists = connection.execute(
                """
                SELECT 1 FROM control_plane_identities
                WHERE kind = ? AND id = ?
                """,
                (agent_kind, agent_id),
            ).fetchone()
            if agent_exists is None:
                raise IdentityNotFoundError(
                    f"Agent identity {agent_kind}:{agent_id} was not found."
                )

            # Verifica che l'identità che assegna esista.
            assigner_exists = connection.execute(
                """
                SELECT 1 FROM control_plane_identities
                WHERE kind = ? AND id = ?
                """,
                (assigned_by_kind, assigned_by_id),
            ).fetchone()
            if assigner_exists is None:
                raise IdentityNotFoundError(
                    f"Assigner identity {assigned_by_kind}:{assigned_by_id} was not found."
                )

            # Verifica che non esista già un'assegnazione attiva.
            existing = connection.execute(
                """
                SELECT 1 FROM control_plane_agent_assignments
                WHERE agent_kind = ? AND agent_id = ? AND mission_id = ? AND status = 'active'
                """,
                (agent_kind, agent_id, mission_id),
            ).fetchone()
            if existing is not None:
                raise DuplicateDeclarationError(
                    f"Agent {agent_kind}:{agent_id} is already assigned to mission {mission_id}."
                )

            connection.execute(
                """
                INSERT INTO control_plane_agent_assignments
                    (id, agent_kind, agent_id, mission_id, assigned_at,
                     assigned_by_kind, assigned_by_id, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
                """,
                (
                    assignment_id,
                    agent_kind,
                    agent_id,
                    mission_id,
                    occurred_at,
                    assigned_by_kind,
                    assigned_by_id,
                ),
            )
            self._append_audit(
                connection,
                action="agent.assigned",
                subject_kind=agent_kind,
                subject_id=agent_id,
                details={
                    "assignment_id": assignment_id,
                    "mission_id": mission_id,
                    "assigned_by": f"{assigned_by_kind}:{assigned_by_id}",
                },
                occurred_at=occurred_at,
            )
        return self.get_agent_assignment(assignment_id)

    def revoke_agent_from_mission(
        self,
        *,
        assignment_id: str,
        revoked_by_kind: str,
        revoked_by_id: str,
    ) -> dict[str, Any] | None:
        """Revoca un'assegnazione agente-missione (imposta status 'revoked')."""
        occurred_at = _now()
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT id, agent_kind, agent_id, mission_id, status
                FROM control_plane_agent_assignments WHERE id = ?
                """,
                (assignment_id,),
            ).fetchone()
            if row is None:
                return None
            if row["status"] != "active":
                raise ValueError(
                    f"Assignment {assignment_id} is not active (status={row['status']})."
                )

            # Verifica che l'identità che revoca esista.
            revoker_exists = connection.execute(
                """
                SELECT 1 FROM control_plane_identities
                WHERE kind = ? AND id = ?
                """,
                (revoked_by_kind, revoked_by_id),
            ).fetchone()
            if revoker_exists is None:
                raise IdentityNotFoundError(
                    f"Revoker identity {revoked_by_kind}:{revoked_by_id} was not found."
                )

            connection.execute(
                """
                UPDATE control_plane_agent_assignments
                SET status = 'revoked'
                WHERE id = ?
                """,
                (assignment_id,),
            )
            self._append_audit(
                connection,
                action="agent.revoked",
                subject_kind=row["agent_kind"],
                subject_id=row["agent_id"],
                details={
                    "assignment_id": assignment_id,
                    "mission_id": row["mission_id"],
                    "revoked_by": f"{revoked_by_kind}:{revoked_by_id}",
                },
                occurred_at=occurred_at,
            )
        return self.get_agent_assignment(assignment_id)

    def get_agent_assignment(self, assignment_id: str) -> dict[str, Any] | None:
        """Restituisce un'assegnazione agente-missione per ID."""
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT id, agent_kind, agent_id, mission_id, assigned_at,
                       assigned_by_kind, assigned_by_id, status
                FROM control_plane_agent_assignments WHERE id = ?
                """,
                (assignment_id,),
            ).fetchone()
        return self._decode_agent_assignment(row) if row is not None else None

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
        """Elenca assegnazioni agente-missione con filtri opzionali."""
        clauses: list[str] = []
        params: list[Any] = []
        if agent_kind is not None:
            clauses.append("agent_kind = ?")
            params.append(agent_kind)
        if agent_id is not None:
            clauses.append("agent_id = ?")
            params.append(agent_id)
        if mission_id is not None:
            clauses.append("mission_id = ?")
            params.append(mission_id)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connection() as connection:
            rows = connection.execute(
                f"""
                SELECT id, agent_kind, agent_id, mission_id, assigned_at,
                       assigned_by_kind, assigned_by_id, status
                FROM control_plane_agent_assignments {where}
                ORDER BY assigned_at DESC, id LIMIT ? OFFSET ?
                """,
                (*params, limit, offset),
            ).fetchall()
        return [
            self._decode_agent_assignment(row) for row in rows
        ]

    @staticmethod
    def _decode_agent_assignment(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "agent": {"kind": row["agent_kind"], "id": row["agent_id"]},
            "mission_id": row["mission_id"],
            "assigned_at": row["assigned_at"],
            "assigned_by": {
                "kind": row["assigned_by_kind"],
                "id": row["assigned_by_id"],
            },
            "status": row["status"],
        }

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
        """Crea un task in background in coda persistente.

        Il task viene inserito con status 'pending' e può essere eseguito
        da un worker esterno. Non viene avviato automaticamente qui.
        """
        occurred_at = _now()
        task_id = str(uuid.uuid4())
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO background_tasks
                    (id, task_type, payload_json, status, created_at,
                     timeout_seconds, max_retries, retry_count)
                VALUES (?, ?, ?, 'pending', ?, ?, ?, 0)
                """,
                (
                    task_id,
                    task_type,
                    _json(payload),
                    occurred_at,
                    timeout_seconds,
                    max_retries,
                ),
            )
            self._append_audit(
                connection,
                action="background_task.created",
                subject_kind="service",
                subject_id=_AUDIT_ACTOR_ID,
                details={
                    "task_id": task_id,
                    "task_type": task_type,
                    "timeout_seconds": timeout_seconds,
                    "max_retries": max_retries,
                },
                occurred_at=occurred_at,
            )
        return self.get_background_task(task_id)

    def get_background_task(self, task_id: str) -> dict[str, Any] | None:
        """Restituisce un task in background per ID."""
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT id, task_type, payload_json, status, created_at,
                       started_at, completed_at, result_json, error_json,
                       timeout_seconds, max_retries, retry_count
                FROM background_tasks WHERE id = ?
                """,
                (task_id,),
            ).fetchone()
        return self._decode_background_task(row) if row is not None else None

    def list_background_tasks(
        self,
        *,
        task_type: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Elenca task in background con filtri opzionali."""
        clauses: list[str] = []
        params: list[Any] = []
        if task_type is not None:
            clauses.append("task_type = ?")
            params.append(task_type)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connection() as connection:
            rows = connection.execute(
                f"""
                SELECT id, task_type, payload_json, status, created_at,
                       started_at, completed_at, result_json, error_json,
                       timeout_seconds, max_retries, retry_count
                FROM background_tasks {where}
                ORDER BY created_at DESC, id LIMIT ? OFFSET ?
                """,
                (*params, limit, offset),
            ).fetchall()
        return [self._decode_background_task(row) for row in rows]

    def update_background_task_status(
        self,
        *,
        task_id: str,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> dict[str, Any] | None:
        """Aggiorna lo status di un task in background.

        Status validi: pending, running, completed, cancelled, failed.
        """
        valid_statuses = {"pending", "running", "completed", "cancelled", "failed"}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}")

        occurred_at = _now()
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT id, status, started_at FROM background_tasks WHERE id = ?
                """,
                (task_id,),
            ).fetchone()
            if row is None:
                return None

            if row["status"] in ("completed", "cancelled", "failed"):
                raise ValueError(
                    f"Task {task_id} is already in terminal status {row['status']}."
                )

            started_at = row["started_at"]
            if status == "running" and started_at is None:
                started_at = occurred_at

            connection.execute(
                """
                UPDATE background_tasks
                SET status = ?, started_at = ?, completed_at = ?,
                    result_json = ?, error_json = ?
                WHERE id = ?
                """,
                (
                    status,
                    started_at,
                    occurred_at if status in ("completed", "cancelled", "failed") else None,
                    _json(result) if result is not None else None,
                    error,
                    task_id,
                ),
            )
            self._append_audit(
                connection,
                action=f"background_task.{status}",
                subject_kind="service",
                subject_id=_AUDIT_ACTOR_ID,
                details={
                    "task_id": task_id,
                    "result": result,
                    "error": error,
                },
                occurred_at=occurred_at,
            )
        return self.get_background_task(task_id)

    def cancel_background_task(self, task_id: str) -> dict[str, Any] | None:
        """Cancella un task in background se è ancora pending."""
        return self.update_background_task_status(
            task_id=task_id,
            status="cancelled",
        )

    def list_overdue_tasks(self) -> list[dict[str, Any]]:
        """Restituisce task 'running' che hanno superato il timeout."""
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT id, task_type, payload_json, status, created_at,
                       started_at, completed_at, result_json, error_json,
                       timeout_seconds, max_retries, retry_count
                FROM background_tasks
                WHERE status = 'running'
                  AND started_at IS NOT NULL
                """
            ).fetchall()
        now = _now()
        overdue: list[dict[str, Any]] = []
        for row in rows:
            task = self._decode_background_task(row)
            started = task.get("started_at")
            timeout_s = task.get("timeout_seconds", 300)
            if started:
                from datetime import datetime, timezone
                started_dt = datetime.fromisoformat(
                    started.replace("Z", "+00:00")
                )
                now_dt = datetime.now(timezone.utc)
                elapsed = (now_dt - started_dt).total_seconds()
                if elapsed > timeout_s:
                    overdue.append(task)
        return overdue

    def increment_retry_count(self, task_id: str) -> dict[str, Any] | None:
        """Incrementa il contatore di retry di un task."""
        with self._connection() as connection:
            row = connection.execute(
                "SELECT retry_count, max_retries FROM background_tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
            if row is None:
                return None
            new_count = int(row["retry_count"]) + 1
            max_retries = int(row["max_retries"])
            connection.execute(
                "UPDATE background_tasks SET retry_count = ? WHERE id = ?",
                (new_count, task_id),
            )
            self._append_audit(
                connection,
                action="background_task.retry",
                subject_kind="service",
                subject_id=_AUDIT_ACTOR_ID,
                details={
                    "task_id": task_id,
                    "retry_count": new_count,
                    "max_retries": max_retries,
                },
                occurred_at=_now(),
            )
        return self.get_background_task(task_id)

    @staticmethod
    def _decode_background_task(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "task_type": row["task_type"],
            "payload": json.loads(row["payload_json"]) if row["payload_json"] else {},
            "status": row["status"],
            "created_at": row["created_at"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "error": row["error_json"],
            "timeout_seconds": row["timeout_seconds"],
            "max_retries": row["max_retries"],
            "retry_count": row["retry_count"],
        }

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
        """Propone una modifica al codice (patch) per revisione.

        La proposta NON viene applicata automaticamente. Richiede
        approvazione esplicita tramite approve_patch_proposal().
        """
        occurred_at = _now()
        proposal_id = str(uuid.uuid4())
        with self._connection() as connection:
            # Verifica che il proponente esista.
            proposer_exists = connection.execute(
                """
                SELECT 1 FROM control_plane_identities
                WHERE kind = ? AND id = ?
                """,
                (proposed_by_kind, proposed_by_id),
            ).fetchone()
            if proposer_exists is None:
                raise IdentityNotFoundError(
                    f"Proposer identity {proposed_by_kind}:{proposed_by_id} was not found."
                )

            connection.execute(
                """
                INSERT INTO evolution_patch_proposals
                    (id, title, description, target_file, patch_content,
                     status, proposed_by_kind, proposed_by_id,
                     proposed_at, reviewed_by_kind, reviewed_by_id,
                     reviewed_at, approval_reason)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, NULL, NULL, NULL, NULL)
                """,
                (
                    proposal_id,
                    title,
                    description,
                    target_file,
                    patch_content,
                    proposed_by_kind,
                    proposed_by_id,
                    occurred_at,
                ),
            )
            self._append_audit(
                connection,
                action="evolution_patch.proposed",
                subject_kind=proposed_by_kind,
                subject_id=proposed_by_id,
                details={
                    "proposal_id": proposal_id,
                    "title": title,
                    "target_file": target_file,
                },
                occurred_at=occurred_at,
            )
        return self.get_patch_proposal(proposal_id)

    def get_patch_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        """Restituisce una proposta di patch per ID."""
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT id, title, description, target_file, patch_content,
                       status, proposed_by_kind, proposed_by_id, proposed_at,
                       reviewed_by_kind, reviewed_by_id, reviewed_at,
                       approval_reason
                FROM evolution_patch_proposals WHERE id = ?
                """,
                (proposal_id,),
            ).fetchone()
        return self._decode_patch_proposal(row) if row is not None else None

    def list_patch_proposals(
        self,
        *,
        status: str | None = None,
        proposed_by_kind: str | None = None,
        proposed_by_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Elenca proposte di patch con filtri opzionali."""
        clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if proposed_by_kind is not None:
            clauses.append("proposed_by_kind = ?")
            params.append(proposed_by_kind)
        if proposed_by_id is not None:
            clauses.append("proposed_by_id = ?")
            params.append(proposed_by_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connection() as connection:
            rows = connection.execute(
                f"""
                SELECT id, title, description, target_file, patch_content,
                       status, proposed_by_kind, proposed_by_id, proposed_at,
                       reviewed_by_kind, reviewed_by_id, reviewed_at,
                       approval_reason
                FROM evolution_patch_proposals {where}
                ORDER BY proposed_at DESC, id LIMIT ? OFFSET ?
                """,
                (*params, limit, offset),
            ).fetchall()
        return [self._decode_patch_proposal(row) for row in rows]

    def approve_patch_proposal(
        self,
        *,
        proposal_id: str,
        reviewed_by_kind: str,
        reviewed_by_id: str,
        approval_reason: str,
    ) -> dict[str, Any] | None:
        """Approva una proposta di patch.

        L'approvazione NON applica il patch automaticamente. Registra
        solo la decisione di approvazione. L'applicazione effettiva
        richiede un intervento manuale separato.
        """
        if not approval_reason or not approval_reason.strip():
            raise ValueError("Approval reason is required.")
        occurred_at = _now()
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT id, status FROM evolution_patch_proposals WHERE id = ?
                """,
                (proposal_id,),
            ).fetchone()
            if row is None:
                return None
            if row["status"] != "pending":
                raise ValueError(
                    f"Proposal {proposal_id} is not pending (status={row['status']})."
                )

            # Verifica che il revisore esista.
            reviewer_exists = connection.execute(
                """
                SELECT 1 FROM control_plane_identities
                WHERE kind = ? AND id = ?
                """,
                (reviewed_by_kind, reviewed_by_id),
            ).fetchone()
            if reviewer_exists is None:
                raise IdentityNotFoundError(
                    f"Reviewer identity {reviewed_by_kind}:{reviewed_by_id} was not found."
                )

            connection.execute(
                """
                UPDATE evolution_patch_proposals
                SET status = 'approved', reviewed_by_kind = ?,
                    reviewed_by_id = ?, reviewed_at = ?,
                    approval_reason = ?
                WHERE id = ?
                """,
                (
                    reviewed_by_kind,
                    reviewed_by_id,
                    occurred_at,
                    approval_reason.strip(),
                    proposal_id,
                ),
            )
            self._append_audit(
                connection,
                action="evolution_patch.approved",
                subject_kind=reviewed_by_kind,
                subject_id=reviewed_by_id,
                details={
                    "proposal_id": proposal_id,
                    "approval_reason": approval_reason.strip(),
                },
                occurred_at=occurred_at,
            )
        return self.get_patch_proposal(proposal_id)

    def reject_patch_proposal(
        self,
        *,
        proposal_id: str,
        reviewed_by_kind: str,
        reviewed_by_id: str,
        rejection_reason: str,
    ) -> dict[str, Any] | None:
        """Rifiuta una proposta di patch."""
        if not rejection_reason or not rejection_reason.strip():
            raise ValueError("Rejection reason is required.")
        occurred_at = _now()
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT id, status FROM evolution_patch_proposals WHERE id = ?
                """,
                (proposal_id,),
            ).fetchone()
            if row is None:
                return None
            if row["status"] != "pending":
                raise ValueError(
                    f"Proposal {proposal_id} is not pending (status={row['status']})."
                )

            reviewer_exists = connection.execute(
                """
                SELECT 1 FROM control_plane_identities
                WHERE kind = ? AND id = ?
                """,
                (reviewed_by_kind, reviewed_by_id),
            ).fetchone()
            if reviewer_exists is None:
                raise IdentityNotFoundError(
                    f"Reviewer identity {reviewed_by_kind}:{reviewed_by_id} was not found."
                )

            connection.execute(
                """
                UPDATE evolution_patch_proposals
                SET status = 'rejected', reviewed_by_kind = ?,
                    reviewed_by_id = ?, reviewed_at = ?,
                    approval_reason = ?
                WHERE id = ?
                """,
                (
                    reviewed_by_kind,
                    reviewed_by_id,
                    occurred_at,
                    rejection_reason.strip(),
                    proposal_id,
                ),
            )
            self._append_audit(
                connection,
                action="evolution_patch.rejected",
                subject_kind=reviewed_by_kind,
                subject_id=reviewed_by_id,
                details={
                    "proposal_id": proposal_id,
                    "rejection_reason": rejection_reason.strip(),
                },
                occurred_at=occurred_at,
            )
        return self.get_patch_proposal(proposal_id)

    @staticmethod
    def _decode_patch_proposal(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "target_file": row["target_file"],
            "patch_content": row["patch_content"],
            "status": row["status"],
            "proposed_by": {
                "kind": row["proposed_by_kind"],
                "id": row["proposed_by_id"],
            },
            "proposed_at": row["proposed_at"],
            "reviewed_by": (
                {
                    "kind": row["reviewed_by_kind"],
                    "id": row["reviewed_by_id"],
                }
                if row["reviewed_by_kind"] is not None
                else None
            ),
            "reviewed_at": row["reviewed_at"],
            "approval_reason": row["approval_reason"],
        }

    # ------------------------------------------------------------------
    # General preferences (M5 Punto 6 — Settings e Network Center)
    # ------------------------------------------------------------------

    def get_preference(self, key: str) -> dict[str, Any] | None:
        """Restituisce una preferenza generale per chiave."""
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT key, value_json, updated_at FROM general_preferences
                WHERE key = ?
                """,
                (key,),
            ).fetchone()
        if row is None:
            return None
        return {
            "key": row["key"],
            "value": json.loads(row["value_json"]),
            "updated_at": row["updated_at"],
        }

    def set_preference(
        self,
        *,
        key: str,
        value: Any,
        updated_by_kind: str,
        updated_by_id: str,
    ) -> dict[str, Any]:
        """Imposta o aggiorna una preferenza generale."""
        if not key or not key.strip():
            raise ValueError("Preference key is required.")
        occurred_at = _now()
        value_json = json.dumps(value, ensure_ascii=False, sort_keys=True)
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO general_preferences (key, value_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (key.strip(), value_json, occurred_at),
            )
            self._append_audit(
                connection,
                action="preference.set",
                subject_kind=updated_by_kind,
                subject_id=updated_by_id,
                details={"key": key.strip(), "value": value},
                occurred_at=occurred_at,
            )
        return self.get_preference(key)

    def list_preferences(self) -> list[dict[str, Any]]:
        """Elenca tutte le preferenze generali."""
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT key, value_json, updated_at FROM general_preferences
                ORDER BY key
                """
            ).fetchall()
        return [
            {
                "key": row["key"],
                "value": json.loads(row["value_json"]),
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    @staticmethod
    def _append_audit(
        connection: sqlite3.Connection,
        *,
        action: str,
        subject_kind: str,
        subject_id: str,
        details: dict[str, Any],
        occurred_at: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO control_plane_audit_events (
                id, occurred_at, actor_kind, actor_id, action,
                subject_kind, subject_id, outcome, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'recorded', ?)
            """,
            (
                str(uuid.uuid4()),
                occurred_at,
                _AUDIT_ACTOR_KIND,
                _AUDIT_ACTOR_ID,
                action,
                subject_kind,
                subject_id,
                _json(details),
            ),
        )
