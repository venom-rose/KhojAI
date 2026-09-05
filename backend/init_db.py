"""Database initialization script for local development and testing."""

import asyncio
import os
import sys

# Ensure backend can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database.base import Base
from backend.app.database.session import engine
from backend.app.models import *


async def init_database():
    print(f"Initializing database schema on {engine.url}...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables initialized successfully.")


if __name__ == "__main__":
    asyncio.run(init_database())
