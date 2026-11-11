"""Knowledge Maintenance service for J.A.C.K. M4.7 Validation & Maintenance.

Implements controlled maintenance operations:
- Duplicate detection
- Stale information identification
- Orphan detection
- Broken provenance detection
- Index health
- Embedding consistency
- Graph consistency
- Database integrity
- Knowledge quality reporting

Does NOT physically delete information automatically.
All operations are read-only or produce reports; destructive actions require
explicit user action through existing API endpoints.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from app.knowledge.repository import KnowledgeRepository

logger = logging.getLogger("jack.backend.knowledge")

# Stale threshold: items not updated for this many days are considered stale
STALE_DAYS_DEFAULT = 180


@dataclass
class DuplicateItemReport:
    item_id: str
    title: str
    content_hash: str
    duplicate_count: int
    item_ids: list[str]


@dataclass
class StaleItemReport:
    item_id: str
    title: str
    updated_at: str
    days_since_update: int


@dataclass
class OrphanItemReport:
    item_id: str
    title: str
    reason: str  # "no_domain" | "no_links" | "no_source"


@dataclass
class BrokenProvenanceReport:
    item_id: str
    title: str
    source_id: str | None
    reason: str


@dataclass
class MaintenanceReport:
    duplicate_items: list[DuplicateItemReport] = field(default_factory=list)
    stale_items: list[StaleItemReport] = field(default_factory=list)
    orphan_items: list[OrphanItemReport] = field(default_factory=list)
    broken_provenance: list[BrokenProvenanceReport] = field(default_factory=list)
    embedding_consistency: dict[str, Any] = field(default_factory=dict)
    graph_consistency: dict[str, Any] = field(default_factory=list)
    database_integrity: dict[str, Any] = field(default_factory=dict)
    generated_at: str = ""


class MaintenanceService:
    """Maintenance operations for the Knowledge Engine.

    All methods are read-only or produce reports. No physical deletion
    is performed automatically.
    """

    def __init__(self, repository: KnowledgeRepository) -> None:
        self.repository = repository
        self._content_hash_ensured = False

    def _ensure_content_hash_column(self) -> None:
        """Add content_hash column to knowledge_items if missing."""
        if self._content_hash_ensured:
            return
        with sqlite3.connect(
            self.repository.database_path, timeout=10
        ) as connection:
            connection.row_factory = sqlite3.Row
            columns = {
                str(row["name"])
                for row in connection.execute(
                    "PRAGMA table_info(knowledge_items)"
                ).fetchall()
            }
            if "content_hash" not in columns:
                connection.execute(
                    "ALTER TABLE knowledge_items ADD COLUMN content_hash TEXT"
                )
                connection.commit()
        self._content_hash_ensured = True

    def run_full_maintenance(
        self,
        stale_days: int = STALE_DAYS_DEFAULT,
    ) -> MaintenanceReport:
        """Run all maintenance checks and return a consolidated report."""
        report = MaintenanceReport()
        report.generated_at = datetime.now(timezone.utc).isoformat(
            timespec="milliseconds"
        ).replace("+00:00", "Z")

        report.duplicate_items = self.find_duplicate_items()
        report.stale_items = self.find_stale_items(stale_days=stale_days)
        report.orphan_items = self.find_orphan_items()
        report.broken_provenance = self.find_broken_provenance()
        report.embedding_consistency = self.check_embedding_consistency()
        report.graph_consistency = self.check_graph_consistency()
        report.database_integrity = self.check_database_integrity()

        return report

    # ------------------------------------------------------------------
    # Duplicate detection
    # ------------------------------------------------------------------

    def find_duplicate_items(self) -> list[DuplicateItemReport]:
        """Find items with identical content (same content hash)."""
        self._ensure_content_hash_column()
        with sqlite3.connect(
            self.repository.database_path, timeout=10
        ) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            rows = connection.execute(
                """
                SELECT content_hash, COUNT(*) as cnt, GROUP_CONCAT(id) as ids,
                       GROUP_CONCAT(title) as titles
                FROM knowledge_items
                WHERE content_hash IS NOT NULL AND content_hash != ''
                GROUP BY content_hash
                HAVING cnt > 1
                """
            ).fetchall()
        reports: list[DuplicateItemReport] = []
        for row in rows:
            ids = [i.strip() for i in str(row["ids"]).split(",") if i.strip()]
            titles = [t.strip() for t in str(row["titles"]).split(",") if t.strip()]
            reports.append(
                DuplicateItemReport(
                    item_id=ids[0] if ids else "",
                    title=titles[0] if titles else "",
                    content_hash=str(row["content_hash"]),
                    duplicate_count=int(row["cnt"]),
                    item_ids=ids,
                )
            )
        return reports

    # ------------------------------------------------------------------
    # Stale information
    # ------------------------------------------------------------------

    def find_stale_items(self, stale_days: int = STALE_DAYS_DEFAULT) -> list[StaleItemReport]:
        """Find items not updated for more than stale_days."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=stale_days)).isoformat(
            timespec="milliseconds"
        ).replace("+00:00", "Z")
        with sqlite3.connect(
            self.repository.database_path, timeout=10
        ) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            rows = connection.execute(
                """
                SELECT id, title, updated_at
                FROM knowledge_items
                WHERE updated_at < ?
                ORDER BY updated_at ASC
                """,
                (cutoff,),
            ).fetchall()
        reports: list[StaleItemReport] = []
        cutoff_dt = datetime.fromisoformat(cutoff.replace("Z", "+00:00"))
        for row in rows:
            updated = str(row["updated_at"])
            try:
                updated_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                days = (datetime.now(timezone.utc) - updated_dt).days
            except Exception:
                days = stale_days + 1
            reports.append(
                StaleItemReport(
                    item_id=str(row["id"]),
                    title=str(row["title"]),
                    updated_at=updated,
                    days_since_update=days,
                )
            )
        return reports

    # ------------------------------------------------------------------
    # Orphan detection
    # ------------------------------------------------------------------

    def find_orphan_items(self) -> list[OrphanItemReport]:
        """Find items with no domain, no links, or no source."""
        reports: list[OrphanItemReport] = []

        # Items with no valid domain
        with sqlite3.connect(
            self.repository.database_path, timeout=10
        ) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")

            # Items whose domain_id doesn't exist in knowledge_domains
            rows = connection.execute(
                """
                SELECT ki.id, ki.title
                FROM knowledge_items ki
                LEFT JOIN knowledge_domains kd ON ki.domain_id = kd.id
                WHERE kd.id IS NULL
                """
            ).fetchall()
            for row in rows:
                reports.append(
                    OrphanItemReport(
                        item_id=str(row["id"]),
                        title=str(row["title"]),
                        reason="no_domain",
                    )
                )

            # Items with no links at all
            rows = connection.execute(
                """
                SELECT ki.id, ki.title
                FROM knowledge_items ki
                WHERE ki.id NOT IN (
                    SELECT DISTINCT from_id FROM knowledge_links
                    UNION
                    SELECT DISTINCT to_id FROM knowledge_links
                )
                """
            ).fetchall()
            for row in rows:
                # Avoid duplicates from no_domain check
                if not any(r.item_id == str(row["id"]) for r in reports):
                    reports.append(
                        OrphanItemReport(
                            item_id=str(row["id"]),
                            title=str(row["title"]),
                            reason="no_links",
                        )
                    )

        return reports

    # ------------------------------------------------------------------
    # Broken provenance
    # ------------------------------------------------------------------

    def find_broken_provenance(self) -> list[BrokenProvenanceReport]:
        """Find items whose source reference is missing or invalid."""
        reports: list[BrokenProvenanceReport] = []
        with sqlite3.connect(
            self.repository.database_path, timeout=10
        ) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            rows = connection.execute(
                """
                SELECT ki.id, ki.title, ki.source_id
                FROM knowledge_items ki
                WHERE ki.source_type = 'document'
                  AND ki.source_id IS NOT NULL
                  AND ki.source_id != ''
                """
            ).fetchall()
            for row in rows:
                source_id = str(row["source_id"])
                source_exists = connection.execute(
                    "SELECT 1 FROM knowledge_sources WHERE id = ?",
                    (source_id,),
                ).fetchone()
                if not source_exists:
                    reports.append(
                        BrokenProvenanceReport(
                            item_id=str(row["id"]),
                            title=str(row["title"]),
                            source_id=source_id,
                            reason="source_not_found",
                        )
                    )
        return reports

    # ------------------------------------------------------------------
    # Embedding consistency
    # ------------------------------------------------------------------

    def check_embedding_consistency(self) -> dict[str, Any]:
        """Check that published items have embeddings."""
        try:
            with sqlite3.connect(
                self.database_path, timeout=10
            ) as connection:
                connection.row_factory = sqlite3.Row
                connection.execute("PRAGMA foreign_keys = ON")
                total_published = connection.execute(
                    "SELECT COUNT(*) as cnt FROM knowledge_items WHERE item_state = 'published'"
                ).fetchone()["cnt"]
                embedded = connection.execute(
                    """
                    SELECT COUNT(DISTINCT ki.id) as cnt
                    FROM knowledge_items ki
                    INNER JOIN knowledge_embeddings ke ON ki.id = ke.item_id
                    WHERE ki.item_state = 'published'
                    """
                ).fetchone()["cnt"]
        except sqlite3.OperationalError:
            # Embeddings table may not exist yet
            total_published = 0
            with sqlite3.connect(
                self.database_path, timeout=10
            ) as connection:
                connection.row_factory = sqlite3.Row
                connection.execute("PRAGMA foreign_keys = ON")
                total_published = connection.execute(
                    "SELECT COUNT(*) as cnt FROM knowledge_items WHERE item_state = 'published'"
                ).fetchone()["cnt"]
            embedded = 0
        return {
            "total_published_items": int(total_published),
            "items_with_embeddings": int(embedded),
            "missing_embeddings": int(total_published - embedded),
            "consistency_ratio": (
                round(embedded / total_published, 4) if total_published > 0 else 1.0
            ),
        }

    @property
    def database_path(self) -> Path:
        return self.repository.database_path

    # ------------------------------------------------------------------
    # Graph consistency
    # ------------------------------------------------------------------

    def check_graph_consistency(self) -> list[dict[str, Any]]:
        """Find links that reference non-existent items."""
        issues: list[dict[str, Any]] = []
        with sqlite3.connect(
            self.repository.database_path, timeout=10
        ) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            rows = connection.execute(
                """
                SELECT kl.id, kl.from_id, kl.to_id, kl.relation_type
                FROM knowledge_links kl
                LEFT JOIN knowledge_items ki1 ON kl.from_id = ki1.id
                LEFT JOIN knowledge_items ki2 ON kl.to_id = ki2.id
                WHERE ki1.id IS NULL OR ki2.id IS NULL
                """
            ).fetchall()
            for row in rows:
                issues.append(
                    {
                        "link_id": str(row["id"]),
                        "from_id": str(row["from_id"]),
                        "to_id": str(row["to_id"]),
                        "relation_type": str(row["relation_type"]),
                        "issue": "missing_source_or_target",
                    }
                )
        return issues

    # ------------------------------------------------------------------
    # Database integrity
    # ------------------------------------------------------------------

    def check_database_integrity(self) -> dict[str, Any]:
        """Run PRAGMA integrity_check and report results."""
        with sqlite3.connect(
            self.database_path, timeout=10
        ) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute("PRAGMA integrity_check").fetchone()
            result = str(row[0]) if row else "unknown"
        return {
            "integrity_check": result,
            "passed": result == "ok",
            "database": str(self.database_path),
        }
