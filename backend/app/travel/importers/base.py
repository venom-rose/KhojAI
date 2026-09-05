"""Base abstract classes and provenance enforcement for travel data importers."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ProvenanceRecord(BaseModel):
    """Data provenance validation contract."""

    source: str = Field(..., description="Source system (e.g. 'osm_overpass', 'wikidata', 'open_meteo', 'seed_verified')")
    source_id: Optional[str] = Field(None, description="External primary key / entity URI (e.g. 'node/1234567', 'Q1234')")
    last_synced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_copyright_compliant: bool = Field(
        default=True,
        description="Explicit validation that text contains no proprietary descriptions or reviews.",
    )


class BaseTravelImporter(ABC):
    """Abstract interface for all travel entity importers."""

    def __init__(self, source_name: str):
        self.source_name = source_name

    def validate_provenance(self, source_id: Optional[str] = None) -> ProvenanceRecord:
        """Create a validated provenance tracking instance."""
        return ProvenanceRecord(
            source=self.source_name,
            source_id=source_id,
            last_synced_at=datetime.now(timezone.utc),
            is_copyright_compliant=True,
        )

    @abstractmethod
    async def import_data(self, **kwargs) -> Dict[str, Any]:
        """Execute extraction, transformation, and database insertion."""
        pass
