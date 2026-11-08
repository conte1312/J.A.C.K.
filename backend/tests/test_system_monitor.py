from __future__ import annotations

import json
import sqlite3
import stat
import tempfile
import unittest
from pathlib import Path
import zipfile

from app.system.backups import LocalBackupService
from app.system.monitor import SystemMonitor


class SystemMonitorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(
            prefix="jack-system-monitor-"
        )
        self.directory = Path(self.temporary_directory.name)
        self.database_path = self.directory / "memories.sqlite3"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_snapshot_checks_existing_databases_read_only_and_deduplicates_paths(
        self,
    ) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY)")
            connection.execute("PRAGMA user_version = 7")
        missing_path = self.directory / "not-created.sqlite3"

        snapshot = SystemMonitor(
            {
                "Memoria": self.database_path,
                "Conversazioni": self.database_path,
                "Database assente": missing_path,
            }
        ).snapshot()

        self.assertEqual(snapshot["backend"]["status"], "ok")
        self.assertGreaterEqual(snapshot["backend"]["peak_memory_bytes"], 0)
        self.assertGreater(snapshot["disk"]["total_bytes"], 0)
        self.assertEqual(
            [database["name"] for database in snapshot["databases"]],
            ["Memoria", "Database assente"],
        )
        self.assertEqual(snapshot["databases"][0]["status"], "ok")
        self.assertTrue(snapshot["databases"][0]["integrity"])
        self.assertEqual(snapshot["databases"][0]["schema_version"], 7)
        self.assertEqual(snapshot["databases"][1]["status"], "missing")
        self.assertFalse(missing_path.exists())
        self.assertNotIn(str(self.directory), str(snapshot))

    def test_corrupt_database_is_reported_without_hiding_error(self) -> None:
        self.database_path.write_bytes(b"not a sqlite database")

        database = SystemMonitor({"Memoria": self.database_path}).snapshot()[
            "databases"
        ][0]

        self.assertEqual(database["status"], "error")
        self.assertFalse(database["integrity"])
        self.assertIn("file is not a database", database["error"])

    def test_rejects_empty_database_configuration(self) -> None:
        with self.assertRaisesRegex(ValueError, "At least one database path"):
            SystemMonitor({})

    def test_backup_is_consistent_private_and_listed(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("CREATE TABLE sample (value TEXT)")
            connection.execute("INSERT INTO sample VALUES ('persisted')")
            connection.execute("PRAGMA user_version = 3")
        backup_directory = self.directory / "backups"
        service = LocalBackupService(
            {"Memoria": self.database_path},
            backup_directory,
        )

        created = service.create_backup()
        backup_path = backup_directory / created["filename"]
        self.assertTrue(backup_path.exists())
        self.assertEqual(stat.S_IMODE(backup_path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(backup_directory.stat().st_mode), 0o700)
        with zipfile.ZipFile(backup_path) as archive:
            self.assertEqual(
                set(archive.namelist()),
                {"manifest.json", "memories.sqlite3"},
            )
            database_bytes = archive.read("memories.sqlite3")
            staged_db = self.directory / "extracted.sqlite3"
            staged_db.write_bytes(database_bytes)
            with sqlite3.connect(staged_db) as connection:
                self.assertEqual(
                    connection.execute("SELECT value FROM sample").fetchone()[0],
                    "persisted",
                )
                self.assertEqual(
                    connection.execute("PRAGMA quick_check").fetchone()[0],
                    "ok",
                )
        listed = service.list_backups()
        self.assertEqual(listed["backups"][0]["filename"], created["filename"])
        self.assertEqual(listed["directory"], str(backup_directory.resolve()))
        validation = service.validate_backup(created["filename"])
        self.assertTrue(validation["valid"])
        self.assertEqual(validation["missing_optional_databases"], [])
        self.assertIs(validation["databases"][0]["integrity"], True)
        self.assertEqual(validation["databases"][0]["schema_version"], 3)

    def test_backup_validation_accepts_legacy_archive_without_optional_database(
        self,
    ) -> None:
        planning_path = self.directory / "tasks.sqlite3"
        control_plane_path = self.directory / "control-plane.sqlite3"
        for path in (self.database_path, planning_path, control_plane_path):
            with sqlite3.connect(path) as connection:
                connection.execute("CREATE TABLE sample (value TEXT)")
                connection.execute("PRAGMA user_version = 1")
        backup_directory = self.directory / "backups"
        backup_directory.mkdir(mode=0o700)
        filename = "jack-backup-20261108T120000Z-123456abcdef.zip"
        databases = [
            {
                "name": "Memoria e conversazioni",
                "filename": "memories.sqlite3",
                "schema_version": 1,
            },
            {
                "name": "Pianificazione",
                "filename": "tasks.sqlite3",
                "schema_version": 1,
            },
        ]
        manifest = {"format_version": 1, "databases": databases}
        with zipfile.ZipFile(backup_directory / filename, "w") as archive:
            archive.writestr("manifest.json", json.dumps(manifest))
            archive.write(self.database_path, "memories.sqlite3")
            archive.write(planning_path, "tasks.sqlite3")
        service = LocalBackupService(
            {
                "Memoria e conversazioni": self.database_path,
                "Pianificazione": planning_path,
                "Control Plane": control_plane_path,
            },
            backup_directory,
            optional_database_names={"Control Plane"},
        )

        validation = service.validate_backup(filename)

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["missing_optional_databases"], ["Control Plane"])
        self.assertEqual(
            {database["name"] for database in validation["databases"]},
            {"Memoria e conversazioni", "Pianificazione"},
        )

    def test_incomplete_backup_does_not_publish_archive(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("CREATE TABLE sample (value TEXT)")
        service = LocalBackupService(
            {
                "Memoria": self.database_path,
                "Pianificazione": self.directory / "missing.sqlite3",
            },
            self.directory / "backups",
        )

        with self.assertRaisesRegex(FileNotFoundError, "Pianificazione"):
            service.create_backup()

        self.assertEqual(list((self.directory / "backups").glob("*.zip")), [])
        self.assertEqual(
            list((self.directory / "backups").glob(".jack-backup-stage-*")),
            [],
        )

    def test_backup_rejects_duplicate_database_filenames(self) -> None:
        with self.assertRaisesRegex(ValueError, "filenames must be unique"):
            LocalBackupService(
                {
                    "Memoria": self.directory / "memory" / "data.sqlite3",
                    "Pianificazione": self.directory / "planning" / "data.sqlite3",
                },
                self.directory / "backups",
            )

    def test_backup_does_not_publish_corrupt_database(self) -> None:
        self.database_path.write_bytes(b"not a sqlite database")
        backup_directory = self.directory / "backups"
        service = LocalBackupService(
            {"Memoria": self.database_path},
            backup_directory,
        )

        with self.assertRaisesRegex(sqlite3.DatabaseError, "file is not a database"):
            service.create_backup()

        self.assertEqual(list(backup_directory.glob("*.zip")), [])
        self.assertEqual(
            list(backup_directory.glob(".jack-backup-stage-*")),
            [],
        )

    def test_backup_rejects_symlink_directory_without_touching_target(self) -> None:
        target = self.directory / "target"
        target.mkdir()
        target.chmod(0o755)
        backup_link = self.directory / "backups-link"
        backup_link.symlink_to(target, target_is_directory=True)
        service = LocalBackupService(
            {"Memoria": self.database_path},
            backup_link,
        )

        with self.assertRaisesRegex(OSError, "symbolic link"):
            service.list_backups()

        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o755)

    def test_backup_validation_rejects_invalid_filename_and_corrupt_archive(self) -> None:
        service = LocalBackupService(
            {"Memoria": self.database_path},
            self.directory / "backups",
        )
        with self.assertRaisesRegex(ValueError, "Invalid local backup filename"):
            service.validate_backup("../memories.sqlite3")

        self.database_path.parent.joinpath("backups").mkdir(mode=0o700)
        archive_path = self.directory / "backups" / (
            "jack-backup-20261108T120000Z-123456abcdef.zip"
        )
        archive_path.write_bytes(b"not a zip archive")
        archive_path.chmod(0o600)
        with self.assertRaisesRegex(ValueError, "invalid or corrupted"):
            service.validate_backup(archive_path.name)

    def test_backup_validation_rejects_unsafe_archive_entry(self) -> None:
        backup_directory = self.directory / "backups"
        service = LocalBackupService(
            {"Memoria": self.database_path},
            backup_directory,
        )
        backup_directory.mkdir(mode=0o700)
        archive_path = backup_directory / (
            "jack-backup-20261108T120000Z-123456abcdef.zip"
        )
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("manifest.json", "{}")
            archive.writestr("../memories.sqlite3", b"")
        archive_path.chmod(0o600)

        with self.assertRaisesRegex(ValueError, "entries do not match"):
            service.validate_backup(archive_path.name)

    def test_backup_validation_rejects_corrupted_database_and_manifest(self) -> None:
        backup_directory = self.directory / "backups"
        service = LocalBackupService(
            {"Memoria": self.database_path},
            backup_directory,
        )
        backup_directory.mkdir(mode=0o700)
        archive_path = backup_directory / (
            "jack-backup-20261108T120000Z-123456abcdef.zip"
        )
        manifest = {
            "format_version": 1,
            "created_at": "2026-11-08T12:00:00+00:00",
            "databases": [
                {"name": "Memoria", "filename": "memories.sqlite3", "schema_version": 0}
            ],
        }
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("manifest.json", json.dumps(manifest))
            archive.writestr("memories.sqlite3", b"not a database")
        archive_path.chmod(0o600)

        with self.assertRaisesRegex(ValueError, "invalid or corrupted"):
            service.validate_backup(archive_path.name)


if __name__ == "__main__":
    unittest.main()
