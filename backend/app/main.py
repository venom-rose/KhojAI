from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.router import api_v1_router
from backend.app.config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for startup and shutdown routines."""
    # Startup: could verify database connection or redis
    yield
    # Shutdown: dispose resources


def create_application() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title=f"{settings.APP_NAME} API",
        version="1.0.0",
        description=(
            "Production backend for KHOJAI (Hidden India AI) — "
            "A destination intelligence layer and AI trip planner for lesser-known destinations in India."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Logging configuration
    import logging
    import time
    logging.basicConfig(
        level=logging.INFO if not settings.DEBUG else logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("khojai.api")

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.perf_counter()
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(f"{method} {path} - {response.status_code} ({duration_ms}ms, ip={client_ip})")
        return response

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.APP_ENV == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # Mount API routers
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    from fastapi import Request
    from fastapi.responses import JSONResponse
    from backend.app.services.ai.base import AIProviderError

    @app.exception_handler(AIProviderError)
    async def ai_provider_exception_handler(request: Request, exc: AIProviderError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "AI service error",
                "detail": exc.message,
                "provider": exc.provider,
            },
        )

    # Root health probe (rich: includes env details)
    @app.get("/health", tags=["Health"])
    async def root_health():
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "env": settings.APP_ENV,
        }

    # Simple ping — used by Vercel load-balancer and deployment checks.
    # Intentionally has NO database dependency so it always responds fast.
    @app.get("/api/health", tags=["Health"], summary="Simple liveness ping")
    async def api_health_ping():
        """Lightweight liveness probe. Returns 200 OK with no external calls."""
        return {"status": "ok", "service": "khojai-api"}

    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
