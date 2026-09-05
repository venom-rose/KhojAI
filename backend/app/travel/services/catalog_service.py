"""Travel catalog service for hierarchical discovery and rich destination payloads."""

from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.destination import Destination
from backend.app.travel.repositories.destination_repo import DestinationRepository
from backend.app.travel.repositories.geo_repo import GeoRepository
from backend.app.travel.schemas.destination import (
    DestinationCategoryOut,
    DestinationDetailExpandedOut,
    SeasonOut,
    TravelTipOut,
)
from backend.app.travel.schemas.poi import ActivityOut, AttractionOut, HotelOut, RestaurantOut
from backend.app.travel.schemas.transit import TransportationOptionOut, TravelRouteOut


class CatalogService:
    """Catalog exploration, hierarchical navigation, and rich entity assembly."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.dest_repo = DestinationRepository(session)
        self.geo_repo = GeoRepository(session)

    async def get_destination_expanded(self, slug_or_id: str) -> Optional[DestinationDetailExpandedOut]:
        """Fetch destination by slug or UUID and convert into rich expanded schema."""
        dest: Optional[Destination] = None
        try:
            val_uuid = UUID(slug_or_id)
            dest = await self.dest_repo.get_by_id(val_uuid)
        except ValueError:
            dest = await self.dest_repo.get_by_slug(slug_or_id)

        if not dest:
            return None

        # Assemble tags
        tag_list = [t.tag for t in getattr(dest, "tags", [])]

        return DestinationDetailExpandedOut(
            id=dest.id,
            slug=dest.slug,
            name=dest.name,
            state=dest.state,
            region=dest.region,
            category=dest.category,
            best_season=dest.best_season,
            budget=dest.budget,
            trust_score=dest.trust_score,
            description=dest.description,
            image_url=dest.image_url,
            accent_color=dest.accent_color,
            coordinate_x=dest.coordinate_x,
            coordinate_y=dest.coordinate_y,
            demo_note=dest.demo_note,
            latitude=dest.latitude,
            longitude=dest.longitude,
            country_id=dest.country_id,
            state_id=dest.state_id,
            city_id=dest.city_id,
            category_id=dest.category_id,
            is_hidden_gem=dest.is_hidden_gem,
            source=dest.source,
            source_id=dest.source_id,
            last_synced_at=dest.last_synced_at,
            tags=tag_list,
            seasons=[SeasonOut.model_validate(s) for s in getattr(dest, "seasons", [])],
            tips=[TravelTipOut.model_validate(t) for t in getattr(dest, "travel_tips", [])],
            attractions=[AttractionOut.model_validate(a) for a in getattr(dest, "attractions", [])],
            hotels=[HotelOut.model_validate(h) for h in getattr(dest, "hotels", [])],
            restaurants=[RestaurantOut.model_validate(r) for r in getattr(dest, "restaurants", [])],
            activities=[ActivityOut.model_validate(ac) for ac in getattr(dest, "activities", [])],
            transportation_options=[
                TransportationOptionOut.model_validate(to) for to in getattr(dest, "transportation_options", [])
            ],
            routes=[TravelRouteOut.model_validate(tr) for tr in getattr(dest, "travel_routes", [])],
        )

    async def list_destinations(
        self,
        category: Optional[str] = None,
        region: Optional[str] = None,
        state: Optional[str] = None,
        budget: Optional[str] = None,
        is_hidden_gem: Optional[bool] = None,
        search_query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Destination]:
        return await self.dest_repo.list_destinations(
            category=category,
            region=region,
            state=state,
            budget=budget,
            is_hidden_gem=is_hidden_gem,
            search_query=search_query,
            limit=limit,
            offset=offset,
        )

    async def list_nearby(
        self, latitude: float, longitude: float, max_distance_deg: float = 1.0, limit: int = 10
    ) -> Sequence[Destination]:
        return await self.dest_repo.list_nearby(
            latitude=latitude,
            longitude=longitude,
            max_distance_deg=max_distance_deg,
            limit=limit,
        )

    async def get_geographic_hierarchy(self) -> List[Dict[str, Any]]:
        """Return hierarchical Country -> States -> Cities breakdown."""
        countries = await self.geo_repo.list_countries()
        tree = []
        for country in countries:
            country_dict = {
                "id": str(country.id),
                "code": country.code,
                "name": country.name,
                "states": [],
            }
            states = await self.geo_repo.list_states_by_country(country.id)
            for state in states:
                state_dict = {
                    "id": str(state.id),
                    "name": state.name,
                    "region": state.region,
                    "code": state.code,
                    "cities": [],
                }
                cities = await self.geo_repo.list_cities_by_state(state.id)
                for city in cities:
                    state_dict["cities"].append({
                        "id": str(city.id),
                        "name": city.name,
                        "city_code": city.city_code,
                        "latitude": city.latitude,
                        "longitude": city.longitude,
                    })
                country_dict["states"].append(state_dict)
            tree.append(country_dict)
        return tree
