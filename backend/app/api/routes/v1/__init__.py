"""V1 legacy API reference routes (preserved for compatibility).

These routes mirror the original V1 surface so the previous implementation
can be referenced. They are kept functional but are not the target of new
development; J.A.C.K. 2.0 active API lives under /api/v2.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["v1-legacy"])


@router.get("/health", summary="V1 health check")
async def health() -> dict[str, str]:
    return {"status": "ok", "api": "v1", "version": "1.0"}


@router.get("/info", summary="V1 info")
async def info() -> dict[str, str]:
    return {"api": "v1", "note": "legacy reference, preserved from J.A.C.K. V1"}
