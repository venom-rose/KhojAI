import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Contribution, Itinerary


@pytest.mark.asyncio
async def test_get_my_profile_and_stats(client: AsyncClient, db_session: AsyncSession):
    """Test retrieving authenticated user profile with accurate aggregate statistics."""
    # 1. Register user
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "traveler.stats@khojai.in",
            "password": "Password123!",
            "full_name": "Rohan Deshmukh",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    user_id = uuid.UUID(reg_res.json()["user"]["id"])
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Add an itinerary and a contribution belonging to this user
    itinerary = Itinerary(
        user_id=user_id,
        share_token="rohan-ziro-trip",
        title="Rohan's Ziro Trip",
        subtitle="Slow travel · 5 days",
        summary="A valley loop.",
        preferences={"budget": "₹15,000"},
        match_score=92,
        rationale_bullets=["Fits preferences"],
    )
    contribution = Contribution(
        user_id=user_id,
        place_name="Old Ziro Market",
        story_text="A traditional market with local smoked pork and bamboo shoots.",
        status="approved",
    )
    db_session.add_all([itinerary, contribution])
    await db_session.commit()

    # 3. Fetch profile
    profile_res = await client.get("/api/v1/users/me", headers=headers)
    assert profile_res.status_code == 200

    data = profile_res.json()
    assert data["email"] == "traveler.stats@khojai.in"
    assert data["full_name"] == "Rohan Deshmukh"
    assert data["role"] == "user"
    assert data["theme_preference"] == "light"
    assert data["stats"]["saved_itineraries_count"] == 1
    assert data["stats"]["contributions_count"] == 1


@pytest.mark.asyncio
async def test_unauthenticated_profile_access(client: AsyncClient):
    """Test accessing /users/me without credentials returns 401 Unauthorized."""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_profile_info(client: AsyncClient):
    """Test updating personal profile fields (full_name, bio, avatar_url, theme)."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "update.profile@khojai.in",
            "password": "Password123!",
            "full_name": "Original Name",
        },
    )
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    update_payload = {
        "full_name": "Updated Explorer Name",
        "bio": "Travel writer and slow journey documentarian.",
        "avatar_url": "https://example.com/avatar.jpg",
        "theme_preference": "dark",
    }
    patch_res = await client.patch("/api/v1/users/me", json=update_payload, headers=headers)
    assert patch_res.status_code == 200

    data = patch_res.json()
    assert data["full_name"] == "Updated Explorer Name"
    assert data["bio"] == "Travel writer and slow journey documentarian."
    assert data["avatar_url"] == "https://example.com/avatar.jpg"
    assert data["theme_preference"] == "dark"

    # Confirm persistence
    get_res = await client.get("/api/v1/users/me", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["theme_preference"] == "dark"


@pytest.mark.asyncio
async def test_update_profile_invalid_theme(client: AsyncClient):
    """Test updating profile with an unsupported theme value fails validation."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "bad.theme@khojai.in", "password": "Password123!"},
    )
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    patch_res = await client.patch(
        "/api/v1/users/me",
        json={"theme_preference": "neon_cyberpunk"},
        headers=headers,
    )
    assert patch_res.status_code == 422


@pytest.mark.asyncio
async def test_update_travel_and_ai_preferences(client: AsyncClient):
    """Test updating travel preferences and AI personalization settings."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "prefs.user@khojai.in", "password": "Password123!"},
    )
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    pref_payload = {
        "budget": "₹25,000",
        "days": "7 days",
        "style": "Outdoors",
        "interests": ["Nature", "Food", "Outdoors"],
        "group": "Just me",
        "ai_pace": "unhurried",
        "ai_curiosity_level": "high",
    }
    patch_res = await client.patch(
        "/api/v1/users/me/preferences",
        json=pref_payload,
        headers=headers,
    )
    assert patch_res.status_code == 200

    prefs = patch_res.json()["travel_preferences"]
    assert prefs["budget"] == "₹25,000"
    assert prefs["days"] == "7 days"
    assert prefs["style"] == "Outdoors"
    assert "Food" in prefs["interests"]
    assert prefs["ai_curiosity_level"] == "high"


@pytest.mark.asyncio
async def test_user_data_isolation(client: AsyncClient):
    """Ensure User A cannot view or modify User B's profile and preferences."""
    # Register User A
    res_a = await client.post(
        "/api/v1/auth/register",
        json={"email": "user.a@khojai.in", "password": "Password123!", "full_name": "User A"},
    )
    token_a = res_a.json()["access_token"]

    # Register User B
    res_b = await client.post(
        "/api/v1/auth/register",
        json={"email": "user.b@khojai.in", "password": "Password123!", "full_name": "User B"},
    )
    token_b = res_b.json()["access_token"]

    # User A updates profile and preferences
    await client.patch(
        "/api/v1/users/me",
        json={"bio": "User A bio"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    await client.patch(
        "/api/v1/users/me/preferences",
        json={"style": "Road trip"},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    # User B checks their own profile
    profile_b = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert profile_b.status_code == 200
    data_b = profile_b.json()
    assert data_b["full_name"] == "User B"
    assert data_b["bio"] is None
    assert data_b["travel_preferences"] == {}


@pytest.mark.asyncio
async def test_account_deletion_flow(client: AsyncClient):
    """Test that account deletion soft-deletes the user and revokes access."""
    # Register user
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "delete.me@khojai.in", "password": "Password123!"},
    )
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Delete account
    del_res = await client.delete("/api/v1/users/me", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["ok"] is True

    # Immediate subsequent access to /users/me fails
    post_del_res = await client.get("/api/v1/users/me", headers=headers)
    assert post_del_res.status_code in (401, 403)

    # Attempting to log back in fails
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "delete.me@khojai.in", "password": "Password123!"},
    )
    assert login_res.status_code == 401
