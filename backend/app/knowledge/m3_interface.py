"""M3 read-only interface for J.A.C.K. M4.6 Context Builder.

Defines a protocol for read-only access to M3 personal memory.
M4 may consume selected personal context through this interface.
M4 must NOT write to M3 or directly access its repository internals.
Personal data must not be copied into general Knowledge items.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class MemoryReadInterface(Protocol):
    """Read-only interface to M3 Memory Engine.

    Implementations should wrap MemoryRepository and expose only
    read-only operations. M4 depends on this protocol, not on
    MemoryRepository directly.
    """

    def get_item(self, item_id: str) -> dict[str, object] | None:
        """Retrieve a single memory item by ID."""
        ...

    def list_items(
        self,
        *,
        domain_id: str | None = None,
        knowledge_type: str | None = None,
        source_type: str | None = None,
        verification_status: str | None = None,
        item_state: str | None = None,
        is_current: bool | None = None,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, object]]:
        """List memory items with optional filters."""
        ...

    def search_items(
        self,
        query: str,
        *,
        domain_id: str | None = None,
        knowledge_type: str | None = None,
        verification_status: str | None = None,
        item_state: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, object]]:
        """Search memory items by text query."""
        ...

    def audit_log(
        self,
        *,
        item_id: str | None = None,
        action: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        """Retrieve audit log entries (read-only)."""
        ...
