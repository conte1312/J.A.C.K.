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
