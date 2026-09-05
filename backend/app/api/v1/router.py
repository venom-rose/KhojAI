from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.users import router as users_router
from backend.app.api.v1.chat import router as chat_router
from backend.app.api.v1.documents import router as documents_router
from backend.app.api.v1.search import router as search_router
from backend.app.config.settings import settings
from backend.app.database.session import get_db

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(search_router)


@api_v1_router.get(
    "/health",
    tags=["Health"],
    summary="System Health & Diagnostics",
    description="Returns real-time health status of database, AI services, and environment configuration.",
)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Active diagnostic probe for SIH demonstration and production load balancers."""
    diagnostics = {
        "status": "healthy",
        "service": f"{settings.APP_NAME} Backend API",
        "version": "1.0.0",
        "environment": settings.APP_ENV,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "database": "unknown",
            "ai_provider": settings.AI_PROVIDER,
            "embedding_provider": settings.EMBEDDING_PROVIDER,
            "storage": "unknown",
        },
    }

    # 1. Probe database connectivity
    try:
        await db.execute(text("SELECT 1"))
        diagnostics["checks"]["database"] = "healthy"
    except Exception as db_err:
        diagnostics["status"] = "degraded"
        diagnostics["checks"]["database"] = f"unhealthy: {str(db_err)}"

    # 2. Probe storage directory
    try:
        import os
        os.makedirs(settings.MEDIA_DIR, exist_ok=True)
        diagnostics["checks"]["storage"] = "accessible"
    except Exception as storage_err:
        diagnostics["status"] = "degraded"
        diagnostics["checks"]["storage"] = f"inaccessible: {str(storage_err)}"

    status_code = status.HTTP_200_OK if diagnostics["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=diagnostics)

