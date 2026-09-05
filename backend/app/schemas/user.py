import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserProfileUpdateIn(BaseModel):
    """Payload for updating user profile and visual settings."""

    full_name: Optional[str] = Field(None, min_length=1, max_length=150, description="Full or display name")
    avatar_url: Optional[str] = Field(None, max_length=500, description="Avatar image URL")
    bio: Optional[str] = Field(None, max_length=500, description="Short bio")
    theme_preference: Optional[str] = Field(
        None,
        pattern="^(light|dark|system)$",
        description="Theme preference: 'light', 'dark', 'system'",
    )


class TravelPreferencesIn(BaseModel):
    """Payload for updating travel and AI personalization preferences."""

    budget: Optional[str] = Field(None, description="Default budget tier (e.g. '₹15,000')")
    days: Optional[str] = Field(None, description="Default duration (e.g. '5 days')")
    style: Optional[str] = Field(None, description="Default travel style (e.g. 'Slow travel', 'Outdoors')")
    interests: Optional[List[str]] = Field(None, description="Preferred interest tags (e.g. ['Nature', 'Culture'])")
    group: Optional[str] = Field(None, description="Default travel party size (e.g. '2 people')")
    ai_pace: Optional[str] = Field(None, description="Preferred pacing: 'unhurried', 'balanced', 'intense'")
    ai_curiosity_level: Optional[str] = Field(None, description="Appetite for offbeat places: 'high', 'moderate'")


class UserStatsOut(BaseModel):
    """User account aggregate statistics."""

    saved_itineraries_count: int = Field(0, description="Number of saved itineraries")
    contributions_count: int = Field(0, description="Number of submitted field notes")


class UserProfileOut(BaseModel):
    """Complete user profile with preferences and activity stats."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    role: str
    theme_preference: str = "light"
    travel_preferences: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool
    is_verified: bool
    stats: UserStatsOut
    created_at: datetime
    updated_at: datetime
