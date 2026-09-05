# =============================================================================
# Vercel Python Serverless Entrypoint
# =============================================================================
# Vercel's Python runtime discovers this file automatically at api/index.py
# and forwards all /api/* HTTP requests to the ASGI `app` object exported here.
#
# This file is intentionally minimal — the full FastAPI application is defined
# in backend/app/main.py. No application logic lives here.
# =============================================================================

from backend.app.main import app  # noqa: F401  (re-exported for Vercel)

__all__ = ["app"]
