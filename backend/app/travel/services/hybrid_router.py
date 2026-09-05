"""Hybrid Travel Data Router orchestrating Local DB + External APIs + AI Knowledge/RAG."""

from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.travel.services.catalog_service import CatalogService
from backend.app.travel.importers.external_adapters import WeatherAdapter, OverpassOSMAdapter


class HybridTravelRouter:
    """Three-tier intelligence coordinator:

    1. Local Database: Stable, curated ground truth (Coordinates, Seasons, POIs, Stays, Routes).
    2. External Travel APIs: Live transient state (Current weather conditions, live bus/train status, dynamic POIs).
    3. AI Knowledge/RAG: Unstructured editorial depth, regional folklore, and cultural context.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.catalog_service = CatalogService(session)
        self.weather_adapter = WeatherAdapter()
        self.osm_adapter = OverpassOSMAdapter()

    async def resolve_destination_context(
        self,
        slug_or_id: str,
        include_live_weather: bool = True,
        include_live_transit: bool = False,
    ) -> Dict[str, Any]:
        """Aggregate data across the 3 layers into a comprehensive travel dossier."""
        # --- Tier 1: Local Structured Database ---
        destination_data = await self.catalog_service.get_destination_expanded(slug_or_id)
        if not destination_data:
            return {"error": f"Destination '{slug_or_id}' not found in local database."}

        context = {
            "tier1_local_database": destination_data.model_dump(),
            "tier2_external_live_apis": {},
            "tier3_ai_knowledge_rag": {},
        }

        # --- Tier 2: External Travel APIs (Live Transient State) ---
        if include_live_weather and destination_data.latitude and destination_data.longitude:
            try:
                weather_info = await self.weather_adapter.fetch_current_weather(
                    lat=destination_data.latitude,
                    lon=destination_data.longitude,
                )
                context["tier2_external_live_apis"]["current_weather"] = weather_info
            except Exception as e:
                context["tier2_external_live_apis"]["current_weather"] = {
                    "status": "unavailable",
                    "reason": str(e),
                }

        if include_live_transit and destination_data.latitude and destination_data.longitude:
            try:
                transit_hubs = await self.osm_adapter.fetch_nearby_transit_nodes(
                    lat=destination_data.latitude,
                    lon=destination_data.longitude,
                    radius_meters=15000,
                )
                context["tier2_external_live_apis"]["nearby_transit_hubs"] = transit_hubs
            except Exception as e:
                context["tier2_external_live_apis"]["nearby_transit_hubs"] = {
                    "status": "unavailable",
                    "reason": str(e),
                }

        # --- Tier 3: AI Knowledge / RAG (Synthesized Context) ---
        # Synthesize knowledge guidance prompt / RAG context tokens
        context["tier3_ai_knowledge_rag"] = {
            "synthesis_summary": f"Verified destination '{destination_data.name}' in {destination_data.state} ({destination_data.region}). Trust score: {destination_data.trust_score}/100.",
            "cultural_narrative": destination_data.description,
            "demo_advisory": destination_data.demo_note,
            "recommended_focus_areas": [t.title for t in destination_data.tips[:3]],
            "data_freshness": {
                "source": destination_data.source or "curated_editorial",
                "source_id": destination_data.source_id,
                "last_synced_at": destination_data.last_synced_at.isoformat() if destination_data.last_synced_at else None,
            },
        }

        return context
