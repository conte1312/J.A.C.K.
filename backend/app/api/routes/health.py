from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "app": "J.A.C.K.",
        "service": settings.app_name,
        "version": settings.version,
    }

