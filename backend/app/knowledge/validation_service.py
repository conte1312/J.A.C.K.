"""Validation & Versioning service for J.A.C.K. M4.7.

Implements verification system, source evaluation, contradiction detection,
knowledge versioning, and autonomous learning policy (3 levels).
All operations are read-only or produce decisions; no automatic writes
to sensitive knowledge without explicit authorization (Level C).
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.knowledge.graph_service import KnowledgeGraphService
from app.knowledge.repository import KnowledgeRepository

logger = logging.getLogger("jack.backend.knowledge")

# Autonomous learning levels
LEVEL_A = "low_risk"
LEVEL_B = "specialized"
LEVEL_C = "controlled"


@dataclass
class SourceEvaluation:
    source_id: str
    source_title: str
    authority_score: float | None
    reliability: float
    corroboration_count: int
    contradiction_count: int
    overall_trust: float


@dataclass
class VerificationDecision:
    item_id: str
    current_verification: str
    proposed_verification: str
    reason: str
    requires_approval: bool
    auto_approvable: bool


@dataclass
class LearningPolicyDecision:
    level: str
    action: str
    reason: str


class ValidationService:
    """Validation, versioning and autonomous learning policy service."""

    def __init__(
        self,
        repository: KnowledgeRepository,
        graph_service: KnowledgeGraphService | None = None,
    ) -> None:
        self.repository = repository
        self.graph_service = graph_service

    # ------------------------------------------------------------------
    # Source evaluation
    # ------------------------------------------------------------------

    def evaluate_source(
        self,
        source_id: str,
    ) -> SourceEvaluation | None:
        with sqlite3.connect(
            self.repository.database_path, timeout=10
        ) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            row = connection.execute(
                """
                SELECT id, title, authority_score
                FROM knowledge_sources
                WHERE id = ?
                """,
                (source_id,),
            ).fetchone()
        if row is None:
            return None

        authority = row["authority_score"]
        if authority is None:
            authority = 0.5

        corroboration = 0
        contradictions = 0
        with sqlite3.connect(
            self.repository.database_path, timeout=10
        ) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            corroboration = connection.execute(
                "SELECT COUNT(*) as cnt FROM knowledge_items WHERE source_id = ?",
                (source_id,),
            ).fetchone()["cnt"]
            contradictions = connection.execute(
                """
                SELECT COUNT(*) as cnt FROM knowledge_links kl
                JOIN knowledge_items ki1 ON kl.from_id = ki1.id
                JOIN knowledge_items ki2 ON kl.to_id = ki2.id
                WHERE kl.relation_type = 'contradicts'
                  AND (ki1.source_id = ? OR ki2.source_id = ?)
                """,
                (source_id, source_id),
            ).fetchone()["cnt"]

        overall = min(1.0, max(0.0, authority * 0.6 + min(corroboration / 10, 1.0) * 0.4))

        return SourceEvaluation(
            source_id=str(row["id"]),
            source_title=str(row["title"] or ""),
            authority_score=authority,
            reliability=round(authority, 2),
            corroboration_count=int(corroboration),
            contradiction_count=int(contradictions),
            overall_trust=round(overall, 2),
        )

    # ------------------------------------------------------------------
    # Contradiction detection
    # ------------------------------------------------------------------

    def find_contradictions(
        self,
        item_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if self.graph_service is None:
            return []
        return self.graph_service.find_contradictions(item_id=item_id)

    # ------------------------------------------------------------------
    # Knowledge versioning
    # ------------------------------------------------------------------

    def get_version_history(
        self,
        item_id: str,
    ) -> list[dict[str, Any]]:
        with sqlite3.connect(
            self.repository.database_path, timeout=10
        ) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            rows = connection.execute(
                """
                SELECT id, version, content, summary, change_reason,
                       created_at, created_by
                FROM knowledge_versions
                WHERE item_id = ?
                ORDER BY version DESC
                """,
                (item_id,),
            ).fetchall()
        return [
            {
                "id": str(r["id"]),
                "version": int(r["version"]),
                "content": str(r["content"]),
                "summary": str(r["summary"] or ""),
                "change_reason": str(r["change_reason"] or ""),
                "created_at": str(r["created_at"]),
                "created_by": str(r["created_by"]),
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Autonomous learning policy
    # ------------------------------------------------------------------

    def evaluate_learning_policy(
        self,
        source_id: str,
        content_sensitivity: str = "general",
        source_trust: float | None = None,
    ) -> LearningPolicyDecision:
        source_eval = self.evaluate_source(source_id)
        trust = source_trust if source_trust is not None else (
            source_eval.overall_trust if source_eval else 0.0
        )

        if content_sensitivity == "sensitive":
            return LearningPolicyDecision(
                level=LEVEL_C,
                action="require_approval",
                reason="Sensitive content requires explicit authorization",
            )

        if content_sensitivity == "specialized":
            if trust < 0.7:
                return LearningPolicyDecision(
                    level=LEVEL_B,
                    action="keep_provisional",
                    reason="Specialized content with insufficient trust",
                )
            return LearningPolicyDecision(
                level=LEVEL_B,
                action="auto_publish",
                reason="Specialized content with sufficient trust",
            )

        if trust >= 0.6:
            return LearningPolicyDecision(
                level=LEVEL_A,
                action="auto_publish",
                reason="General knowledge from trusted source",
            )
        return LearningPolicyDecision(
            level=LEVEL_A,
            action="keep_provisional",
            reason="General knowledge with low trust",
        )

    # ------------------------------------------------------------------
    # Verification state validation
    # ------------------------------------------------------------------

    def validate_transition(
        self,
        current_state: str,
        target_state: str,
        state_type: str,
    ) -> bool:
        valid_states = {
            "item_state": {"draft", "published", "archived"},
            "process_state": {"pending", "accepted", "rejected", "expired", "published"},
            "verification_status": {"unverified", "provisional", "verified",
                                    "inferred", "contradicted"},
        }
        allowed = valid_states.get(state_type, set())
        if current_state not in allowed or target_state not in allowed:
            return False

        if state_type == "item_state":
            allowed_transitions = {
                ("draft", "published"),
                ("draft", "archived"),
                ("published", "archived"),
            }
            return (current_state, target_state) in allowed_transitions

        if state_type == "process_state":
            if current_state == "pending":
                return target_state in {
                    "accepted", "rejected", "expired", "published"
                }
            return False

        if state_type == "verification_status":
            return True

        return False
