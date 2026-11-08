from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from app.control_plane.repository import (
    ControlPlaneRepository,
    DuplicateDeclarationError,
    IdentityNotFoundError,
)
from app.control_plane.schemas import (
    ApprovalRecordContract,
    AuthorizationDecisionContract,
    CapabilityDeclaration,
    EmergencyStopStatusContract,
    IdentityDeclaration,
    PermissionRequestContract,
    PolicyRuleContract,
)
from app.control_plane.service import ControlPlaneService


class ControlPlaneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(
            prefix="jack-control-plane-"
        )
        self.database_path = Path(self.temporary_directory.name) / "control-plane.sqlite3"
        self.repository = ControlPlaneRepository(self.database_path)
        self.repository.initialize()
        self.service = ControlPlaneService(self.repository)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_identity_kinds_are_distinct_and_declarations_persist(self) -> None:
        agent = self.service.declare_identity(
            {"kind": "agent", "id": "planner", "display_name": "Planner agent"}
        )
        tool = self.service.declare_identity(
            {"kind": "tool", "id": "planner", "display_name": "Planner tool"}
        )

        reopened = ControlPlaneRepository(self.database_path)
        reopened.initialize()
        self.assertEqual(agent["kind"], "agent")
        self.assertEqual(tool["kind"], "tool")
        self.assertEqual(
            len(ControlPlaneService(reopened).list_identities(kind="agent")), 1
        )
        self.assertEqual(
            len(ControlPlaneService(reopened).list_identities(kind="tool")), 1
        )

    def test_capability_is_a_declaration_and_requires_a_registered_owner(self) -> None:
        with self.assertRaises(IdentityNotFoundError):
            self.service.declare_capability(_capability("missing"))

        self.service.declare_identity(
            {"kind": "agent", "id": "planner", "display_name": "Planner"}
        )
        declaration = self.service.declare_capability(_capability("planner"))

        self.assertEqual(declaration["owner"], {"kind": "agent", "id": "planner"})
        self.assertEqual(declaration["operations"], ["read"])
        self.assertNotIn("granted", declaration)
        self.assertNotIn("enabled", declaration)

    def test_declarations_create_persistent_audit_events_atomically(self) -> None:
        self.service.declare_identity(
            {"kind": "agent", "id": "planner", "display_name": "Planner"}
        )
        self.service.declare_capability(_capability("planner"))
        with self.assertRaises(DuplicateDeclarationError):
            self.service.declare_capability(_capability("planner"))

        reopened = ControlPlaneRepository(self.database_path)
        reopened.initialize()
        events = ControlPlaneService(reopened).list_audit_events(limit=20)
        self.assertEqual(
            {event["action"] for event in events},
            {"identity.declared", "capability.declared"},
        )
        self.assertEqual(len(events), 2)
        self.assertTrue(
            all(event["actor"] == {"kind": "service", "id": "control-plane-api"}
                for event in events)
        )

    def test_audit_events_are_immutable_in_sqlite(self) -> None:
        self.service.declare_identity(
            {"kind": "user", "id": "local-user", "display_name": "Local user"}
        )
        with sqlite3.connect(self.database_path) as connection:
            event_id = connection.execute(
                "SELECT id FROM control_plane_audit_events"
            ).fetchone()[0]
            with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable"):
                connection.execute(
                    "UPDATE control_plane_audit_events SET action = 'forged' WHERE id = ?",
                    (event_id,),
                )
            with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable"):
                connection.execute(
                    "DELETE FROM control_plane_audit_events WHERE id = ?",
                    (event_id,),
                )

    def test_scope_and_risk_validation_reject_unsafe_or_malformed_declarations(
        self,
    ) -> None:
        self.service.declare_identity(
            {"kind": "agent", "id": "planner", "display_name": "Planner"}
        )
        invalid = _capability("planner")
        invalid["operations"] = ["read", "read"]
        with self.assertRaisesRegex(ValueError, "unique"):
            self.service.declare_capability(invalid)

        invalid = _capability("planner")
        invalid["risk_level"] = "critical"
        invalid["approval_required"] = False
        with self.assertRaisesRegex(ValueError, "approval"):
            self.service.declare_capability(invalid)

        invalid = _capability("planner")
        invalid["scope"] = {"not_json": {1, 2}}
        with self.assertRaisesRegex(ValueError, "JSON"):
            self.service.declare_capability(invalid)

    def test_schema_contracts_validate_separate_principals_scope_and_duration(self) -> None:
        identity = IdentityDeclaration(
            kind="node", id="local-node", display_name="Local node"
        )
        self.assertEqual(identity.kind, "node")
        permission = PermissionRequestContract(
            requester={"kind": "agent", "id": "planner"},
            resource="planning.tasks",
            operation="read",
            scope={"project_id": "project-1"},
            duration_seconds=300,
            risk_level="normal",
        )
        self.assertEqual(permission.requester.kind, "agent")
        with self.assertRaises(ValidationError):
            PermissionRequestContract(
                requester={"kind": "agent", "id": "planner"},
                resource="planning.tasks",
                operation="read",
                duration_seconds=0,
                risk_level="normal",
            )
        with self.assertRaises(ValidationError):
            CapabilityDeclaration(
                id="read-tasks",
                owner={"kind": "service", "id": "planning-api"},
                description="Read tasks",
                resource="planning.tasks",
                operations=[],
                risk_level="normal",
                approval_required=False,
            )
        with self.assertRaises(ValidationError):
            CapabilityDeclaration(
                id="read-tasks",
                owner={"kind": "service", "id": "planning-api"},
                description="Read tasks",
                resource="planning.tasks",
                operations=["read", "read"],
                risk_level="normal",
                approval_required=False,
            )
        with self.assertRaises(ValidationError):
            AuthorizationDecisionContract(
                outcome="requires_approval",
                approval_required=False,
                reason="Approval is missing.",
            )

        self.assertEqual(
            PolicyRuleContract(
                id="deny-shell",
                resource="terminal",
                operation="execute",
                outcome="deny",
                risk_level="critical",
                approval_required=True,
            ).outcome,
            "deny",
        )
        self.assertEqual(
            ApprovalRecordContract(
                id="approval-1",
                request_id="request-1",
                status="pending",
                requested_by={"kind": "agent", "id": "planner"},
            ).status,
            "pending",
        )
        with self.assertRaises(ValidationError):
            ApprovalRecordContract(
                id="approval-2",
                request_id="request-2",
                status="approved",
                requested_by={"kind": "agent", "id": "planner"},
            )
        self.assertFalse(EmergencyStopStatusContract(active=False).active)

    def test_database_initialization_isolated_and_preserves_existing_rows(self) -> None:
        self.service.declare_identity(
            {"kind": "service", "id": "planning-api", "display_name": "Planning API"}
        )
        with sqlite3.connect(self.database_path) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 1)

        self.repository.initialize()
        self.assertIsNotNone(self.repository.get_identity("service", "planning-api"))

        other_path = Path(self.temporary_directory.name) / "other.sqlite3"
        other_repository = ControlPlaneRepository(other_path)
        other_repository.initialize()
        self.assertEqual(
            ControlPlaneService(other_repository).list_identities(kind="agent"), []
        )
        service_identities = ControlPlaneService(
            other_repository
        ).list_identities(kind="service")
        self.assertEqual(
            [(identity["kind"], identity["id"]) for identity in service_identities],
            [("service", "control-plane-api")],
        )
        self.assertEqual(ControlPlaneService(other_repository).list_audit_events(), [])

    def test_newer_database_schema_is_rejected_without_rewriting(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("CREATE TABLE retained (value TEXT)")
            connection.execute("INSERT INTO retained VALUES ('preserve')")
            connection.execute("PRAGMA user_version = 999")

        with self.assertRaisesRegex(RuntimeError, "newer than this app"):
            self.repository.initialize()
        with sqlite3.connect(self.database_path) as connection:
            self.assertEqual(
                connection.execute("SELECT value FROM retained").fetchone()[0],
                "preserve",
            )
            self.assertEqual(
                connection.execute("PRAGMA user_version").fetchone()[0], 999
            )


def _capability(owner_id: str) -> dict[str, object]:
    return {
        "id": "read-planning-tasks",
        "owner": {"kind": "agent", "id": owner_id},
        "description": "May declare that it can read planning task data.",
        "resource": "planning.tasks",
        "operations": ["read"],
        "scope": {"project_id": "project-1"},
        "risk_level": "normal",
        "approval_required": False,
    }


if __name__ == "__main__":
    unittest.main()
