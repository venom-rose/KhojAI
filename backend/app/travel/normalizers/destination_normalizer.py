"""Destination normalizer converting various data representations into TravelDestination."""

from typing import Any, Dict, List, Optional
from backend.app.travel.schemas.internal import TravelDestination


class DestinationNormalizer:
    """Normalizes raw DB models, dicts, or external provider outputs to TravelDestination."""

    @staticmethod
    def from_db_model(dest_model: Any) -> TravelDestination:
        """Converts an SQLAlchemy Destination model or dict to TravelDestination."""
        if isinstance(dest_model, dict):
            return DestinationNormalizer.from_dict(dest_model)

        slug = getattr(dest_model, "slug", None) or getattr(dest_model, "name", "").lower().replace(" ", "-")
        name = getattr(dest_model, "name", "Unknown Destination")

        # Extract tags safely without triggering lazy loads in async contexts
        raw_tags = []
        try:
            from sqlalchemy import inspect as sa_inspect
            insp = sa_inspect(dest_model)
            if insp and hasattr(insp, "unloaded") and "tags" not in insp.unloaded:
                raw_tags = getattr(dest_model, "tags", [])
        except Exception:
            pass

        if isinstance(raw_tags, list):
            tags = [getattr(t, "tag", str(t)) for t in raw_tags]
        elif isinstance(raw_tags, str):
            tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        else:
            tags = []

        return TravelDestination(
            slug=slug,
            name=name,
            state=getattr(dest_model, "state", None),
            country=getattr(dest_model, "country", "India") or "India",
            country_code=getattr(dest_model, "country_code", "IN") or "IN",
            region=getattr(dest_model, "region", None),
            category=getattr(dest_model, "category", None),
            description=getattr(dest_model, "description", None),
            latitude=getattr(dest_model, "latitude", None),
            longitude=getattr(dest_model, "longitude", None),
            best_season=getattr(dest_model, "best_season", None),
            budget_tier=getattr(dest_model, "budget_tier", None),
            trust_score=getattr(dest_model, "trust_score", 85) or 85,
            image_url=getattr(dest_model, "image_url", None),
            tags=tags,
            provider="local_db",
            provider_id=str(getattr(dest_model, "id", slug)),
            metadata=getattr(dest_model, "meta", {}) if isinstance(getattr(dest_model, "meta", None), dict) else {},
        )

    @staticmethod
    def from_dict(data: Dict[str, Any], provider: str = "local_db") -> TravelDestination:
        """Converts arbitrary dictionary data to TravelDestination."""
        name = data.get("name") or data.get("title") or "Unknown Destination"
        slug = data.get("slug") or name.lower().replace(" ", "-").replace("'", "")
        
        tags = data.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        return TravelDestination(
            slug=slug,
            name=name,
            state=data.get("state") or data.get("state_name"),
            country=data.get("country") or data.get("country_name", "India"),
            country_code=data.get("country_code", "IN"),
            region=data.get("region"),
            category=data.get("category"),
            description=data.get("description") or data.get("overview"),
            latitude=data.get("latitude") or data.get("lat"),
            longitude=data.get("longitude") or data.get("lon") or data.get("lng"),
            best_season=data.get("best_season"),
            budget_tier=data.get("budget_tier"),
            trust_score=data.get("trust_score", 85),
            image_url=data.get("image_url") or data.get("hero_image"),
            tags=tags,
            provider=provider,
            provider_id=str(data.get("id") or data.get("place_id") or slug),
            metadata=data.get("metadata", {}),
        )
