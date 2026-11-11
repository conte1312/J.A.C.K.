"""V2 active API routes for J.A.C.K. 2.0.

New modular endpoints. Each domain registers its own router here.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes.v2.knowledge import router as knowledge_router
from app.api.routes.v2.memories import router as memories_router

router = APIRouter(tags=["v2"])

router.include_router(memories_router)
router.include_router(knowledge_router)

@router.get("/health", summary="V2 health check")
async def health() -> dict[str, str]:
    return {"status": "ok", "api": "v2", "version": "2.0.0"}


@router.get("/info", summary="V2 info")
async def info() -> dict[str, str]:
    return {
        "api": "v2",
        "version": "2.0.0",
        "product": "J.A.C.K. — Just Another Chill Kernel",
        "bind": "127.0.0.1",
    }
