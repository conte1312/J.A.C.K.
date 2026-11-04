from __future__ import annotations

import sqlite3
import stat
import tempfile
import unittest
from pathlib import Path

from app.memory.repository import MemoryRepository


class MemoryMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(
            prefix="jack-memory-migration-"
        )
        self.database_path = Path(self.temporary_directory.name) / "memories.sqlite3"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_legacy_database_migrates_in_place_and_preserves_records(self) -> None:
        self._create_legacy_database()
        original_ids = [f"legacy-{index}" for index in range(5)]

        repository = MemoryRepository(self.database_path)
        repository.initialize()
        repository.initialize()

        records = {record["id"]: record for record in repository.list()}
        self.assertEqual(set(records), set(original_ids))
        self.assertEqual(
            {record["category"] for record in records.values()},
            {"identity", "work", "projects", "preferences", "other"},
        )
        for record in records.values():
            self.assertEqual(record["source_type"], "saved")
            self.assertIsNone(record["source"])
            self.assertEqual(record["verification"], "to_verify")
            self.assertEqual(record["tags"], [])
            self.assertEqual(record["importance"], 3)
            self.assertFalse(record["excluded"])
            self.assertIsNone(record["conversation_id"])
            self.assertIsNone(record["last_used"])
            self.assertEqual(record["created_at"], "2025-01-02T03:04:05Z")
            self.assertEqual(record["updated_at"], "2025-01-02T03:04:05Z")

        with sqlite3.connect(self.database_path) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 2)
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM memories").fetchone()[0],
                5,
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM memory_links").fetchone()[0],
                0,
            )
            foreign_keys = connection.execute(
                "PRAGMA foreign_key_list(memory_links)"
            ).fetchall()
            self.assertEqual(len(foreign_keys), 2)
            connection.execute("PRAGMA foreign_keys = ON")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO memory_links
                    (id, from_id, to_id, relation, relation_key, strength, created_at)
                    VALUES (
                        'orphan', 'missing-a', 'missing-b', 'related',
                        'related', 1, 'now'
                    )
                    """
                )

        backup_path = self.database_path.with_name(
            "memories.sqlite3.pre-v2.bak"
        )
        self.assertTrue(backup_path.exists())
        if stat.S_IMODE(backup_path.stat().st_mode) != 0o600:
            self.fail("Migration backup permissions must be private.")
        with sqlite3.connect(backup_path) as backup:
            self.assertEqual(
                backup.execute("SELECT COUNT(*) FROM memories").fetchone()[0],
                5,
            )
            self.assertEqual(
                backup.execute(
                    "SELECT category FROM memories ORDER BY id LIMIT 1"
                ).fetchone()[0],
                "personale",
            )

    def test_failed_migration_rolls_back_and_keeps_backup(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                "CREATE TABLE memories (id TEXT PRIMARY KEY, title TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO memories(id, title) VALUES ('legacy-1', 'Local title')"
            )

        with self.assertRaisesRegex(RuntimeError, "unsupported schema"):
            MemoryRepository(self.database_path).initialize()

        with sqlite3.connect(self.database_path) as connection:
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(memories)")
            }
            self.assertEqual(columns, {"id", "title"})
            self.assertEqual(
                connection.execute("SELECT title FROM memories").fetchone()[0],
                "Local title",
            )
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 0)
        self.assertTrue(
            self.database_path.with_name("memories.sqlite3.pre-v2.bak").exists()
        )

    def _create_legacy_database(self) -> None:
        categories = ("personale", "lavoro", "progetti", "preferenze", "note")
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE memories (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL CHECK(length(trim(title)) > 0),
                    content TEXT NOT NULL CHECK(length(trim(content)) > 0),
                    category TEXT NOT NULL CHECK(category IN (
                        'personale', 'lavoro', 'progetti', 'preferenze', 'note'
                    )),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.executemany(
                """
                INSERT INTO memories
                (id, title, content, category, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        f"legacy-{index}",
                        f"Title {index}",
                        f"Neutral legacy content {index}",
                        category,
                        "2025-01-02T03:04:05Z",
                        "2025-01-02T03:04:05Z",
                    )
                    for index, category in enumerate(categories)
                ],
            )


if __name__ == "__main__":
    unittest.main()
