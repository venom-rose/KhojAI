"""External API adapters for live weather, OpenStreetMap Overpass transit, and Wikidata facts."""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from backend.app.travel.importers.base import BaseTravelImporter


class WeatherAdapter(BaseTravelImporter):
    """Fetches live meteorological conditions using Open-Meteo (open API, no key required)."""

    def __init__(self):
        super().__init__(source_name="open_meteo")
        self.base_url = "https://api.open-meteo.com/v1/forecast"

    async def fetch_current_weather(self, lat: float, lon: float) -> Dict[str, Any]:
        params = {
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
            "timezone": "auto",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(self.base_url, params=params)
            resp.raise_for_status()
            data = resp.json()

        current = data.get("current", {})
        provenance = self.validate_provenance(source_id=f"coords/{round(lat,4)},{round(lon,4)}")

        return {
            "temperature_c": current.get("temperature_2m"),
            "apparent_temperature_c": current.get("apparent_temperature"),
            "humidity_percent": current.get("relative_humidity_2m"),
            "precipitation_mm": current.get("precipitation"),
            "weather_code": current.get("weather_code"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "source": provenance.source,
            "source_id": provenance.source_id,
            "last_synced_at": provenance.last_synced_at.isoformat(),
        }

    async def import_data(self, **kwargs) -> Dict[str, Any]:
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")
        if lat is None or lon is None:
            raise ValueError("lat and lon are required for WeatherAdapter")
        return await self.fetch_current_weather(lat, lon)


class OverpassOSMAdapter(BaseTravelImporter):
    """Queries OpenStreetMap Overpass API for public transit hubs and geographic landmarks."""

    def __init__(self):
        super().__init__(source_name="osm_overpass")
        self.endpoint = "https://overpass-api.de/api/interpreter"

    async def fetch_nearby_transit_nodes(
        self, lat: float, lon: float, radius_meters: int = 15000
    ) -> List[Dict[str, Any]]:
        query = f"""
        [out:json][timeout:15];
        (
          node["highway"="bus_stop"](around:{radius_meters},{lat},{lon});
          node["railway"="station"](around:{radius_meters},{lat},{lon});
          node["aeroway"="aerodrome"](around:{radius_meters},{lat},{lon});
        );
        out body 10;
        """
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(self.endpoint, data={"data": query})
            resp.raise_for_status()
            data = resp.json()

        elements = data.get("elements", [])
        hubs = []
        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name") or tags.get("name:en") or "Unnamed transit node"
            hub_type = "bus_stop"
            if tags.get("railway") == "station":
                hub_type = "railway_station"
            elif tags.get("aeroway") == "aerodrome":
                hub_type = "airport"

            provenance = self.validate_provenance(source_id=f"node/{el.get('id')}")
            hubs.append({
                "name": name,
                "hub_type": hub_type,
                "latitude": el.get("lat"),
                "longitude": el.get("lon"),
                "source": provenance.source,
                "source_id": provenance.source_id,
                "last_synced_at": provenance.last_synced_at.isoformat(),
            })
        return hubs

    async def import_data(self, **kwargs) -> Dict[str, Any]:
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")
        radius = kwargs.get("radius_meters", 15000)
        if lat is None or lon is None:
            raise ValueError("lat and lon are required for OverpassOSMAdapter")
        hubs = await self.fetch_nearby_transit_nodes(lat, lon, radius)
        return {"transit_hubs": hubs, "count": len(hubs)}


class WikidataAdapter(BaseTravelImporter):
    """Fetches factual, non-copyrighted geographic entity metadata from Wikidata."""

    def __init__(self):
        super().__init__(source_name="wikidata")
        self.sparql_endpoint = "https://query.wikidata.org/sparql"

    async def fetch_entity_facts(self, wikidata_id: str) -> Dict[str, Any]:
        query = f"""
        SELECT ?coord ?elevation WHERE {{
          wd:{wikidata_id} wdt:P625 ?coord .
          OPTIONAL {{ wd:{wikidata_id} wdt:P2044 ?elevation . }}
        }} LIMIT 1
        """
        headers = {"User-Agent": "KhojAI-Travel-Bot/1.0 (info@khojai.local)"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                self.sparql_endpoint,
                params={"query": query, "format": "json"},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        bindings = data.get("results", {}).get("bindings", [])
        provenance = self.validate_provenance(source_id=wikidata_id)

        if not bindings:
            return {"wikidata_id": wikidata_id, "found": False}

        row = bindings[0]
        return {
            "wikidata_id": wikidata_id,
            "found": True,
            "coord_raw": row.get("coord", {}).get("value"),
            "elevation_meters": row.get("elevation", {}).get("value"),
            "source": provenance.source,
            "source_id": provenance.source_id,
            "last_synced_at": provenance.last_synced_at.isoformat(),
        }

    async def import_data(self, **kwargs) -> Dict[str, Any]:
        wikidata_id = kwargs.get("wikidata_id")
        if not wikidata_id:
            raise ValueError("wikidata_id is required for WikidataAdapter")
        return await self.fetch_entity_facts(wikidata_id)
