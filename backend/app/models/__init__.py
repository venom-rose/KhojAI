from backend.app.database.base import Base
from backend.app.models.user import User, Session
from backend.app.models.destination import Destination, DestinationTag, TrustMetric
from backend.app.models.itinerary import Itinerary, ItineraryDay
from backend.app.models.contribution import Contribution
from backend.app.models.community import CommunityStory
from backend.app.models.document import Document, DocumentChunk
from backend.app.models.chat import Conversation, ChatMessage

# Travel Data Layer models
from backend.app.travel.models.geo import Country, State, City
from backend.app.travel.models.destination import DestinationCategory, Season, TravelTip
from backend.app.travel.models.poi import Attraction, Activity, Hotel, Restaurant
from backend.app.travel.models.transit import Airport, TransportationOption, TravelRoute
from backend.app.travel.models.trip import Trip, TripDay, TripItem, UserTravelPreference

__all__ = [
    "Base",
    "User",
    "Session",
    "Destination",
    "DestinationTag",
    "TrustMetric",
    "Itinerary",
    "ItineraryDay",
    "Contribution",
    "CommunityStory",
    "Document",
    "DocumentChunk",
    "Conversation",
    "ChatMessage",
    # Travel Layer
    "Country",
    "State",
    "City",
    "DestinationCategory",
    "Season",
    "TravelTip",
    "Attraction",
    "Activity",
    "Hotel",
    "Restaurant",
    "Airport",
    "TransportationOption",
    "TravelRoute",
    "Trip",
    "TripDay",
    "TripItem",
    "UserTravelPreference",
]

