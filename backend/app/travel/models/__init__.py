"""Travel data layer entity exports and model registry."""

from backend.app.travel.models.geo import Country, State, City
from backend.app.travel.models.destination import DestinationCategory, Season, TravelTip
from backend.app.travel.models.poi import Attraction, Activity, Hotel, Restaurant
from backend.app.travel.models.transit import Airport, TransportationOption, TravelRoute
from backend.app.travel.models.trip import Trip, TripDay, TripItem, UserTravelPreference
from backend.app.models.destination import Destination, DestinationTag, TrustMetric

__all__ = [
    # Geo
    "Country",
    "State",
    "City",
    # Destination & Taxonomy
    "Destination",
    "DestinationCategory",
    "DestinationTag",
    "TrustMetric",
    "Season",
    "TravelTip",
    # Points of Interest (POIs)
    "Attraction",
    "Activity",
    "Hotel",
    "Restaurant",
    # Transit
    "Airport",
    "TransportationOption",
    "TravelRoute",
    # Trip Planning
    "Trip",
    "TripDay",
    "TripItem",
    "UserTravelPreference",
]
