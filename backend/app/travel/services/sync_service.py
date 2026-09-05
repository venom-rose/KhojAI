"""Sync and Provenance Audit Service for tracking external data freshness and compliance."""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Type
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.base import Base


class SyncService:
    """Service verifying provenance metadata, identifying stale entities, and auditing sync recency."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def audit_staleness(self, model_cls: Type[Base], max_age_days: int = 90) -> Dict[str, Any]:
        """Check for entities whose last_synced_at is older than max_age_days or NULL."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

        # Count total
        total_stmt = select(func.count(model_cls.id))
        total_res = await self.session.execute(total_stmt)
        total_count = total_res.scalar_one()

        # Count stale or unsynced
        stale_stmt = select(func.count(model_cls.id)).where(
            (model_cls.last_synced_at.is_(None)) | (model_cls.last_synced_at < cutoff)
        )
        stale_res = await self.session.execute(stale_stmt)
        stale_count = stale_res.scalar_one()

        # Count by source
        source_stmt = select(model_cls.source, func.count(model_cls.id)).group_by(model_cls.source)
        source_res = await self.session.execute(source_stmt)
        sources_breakdown = {s: cnt for s, cnt in source_res.all()}

        return {
            "entity_name": model_cls.__tablename__,
            "total_records": total_count,
            "stale_records": stale_count,
            "freshness_ratio": round((total_count - stale_count) / max(total_count, 1), 3),
            "sources_breakdown": sources_breakdown,
            "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def mark_synced(self, instance: Base, source: Optional[str] = None, source_id: Optional[str] = None) -> None:
        """Stamp an entity with the current UTC timestamp and optional source metadata."""
        if hasattr(instance, "last_synced_at"):
            instance.last_synced_at = datetime.now(timezone.utc)
        if source and hasattr(instance, "source"):
            instance.source = source
        if source_id and hasattr(instance, "source_id"):
            instance.source_id = source_id
        await self.session.flush()
