from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["info"])


@router.get("/info")
async def info() -> dict[str, object]:
    return {
        "name": settings.app_name,
        "version": settings.version,
        "modules": ["health", "info", "memories", "conversations", "ai"],
    }

