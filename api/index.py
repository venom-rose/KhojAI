# =============================================================================
# Vercel Python Serverless Entrypoint
# =============================================================================
# Vercel's Python runtime discovers this file automatically at api/index.py
# and forwards all /api/* HTTP requests to the ASGI `app` object exported here.
#
# This file is intentionally minimal — the full FastAPI application is defined
# in backend/app/main.py. No application logic lives here.
# =============================================================================

import os
import sys

# Ensure repository root is on sys.path for serverless imports
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app.main import app  # noqa: F401  (re-exported for Vercel)

__all__ = ["app"]
