from datetime import timedelta
import pytest
from httpx import AsyncClient

from backend.app.config.settings import settings
from backend.app.security.jwt import create_access_token


@pytest.mark.asyncio
async def test_successful_registration(client: AsyncClient):
    """Test user registration returns 201, JWT token, user info, and sets cookie."""
    payload = {
        "email": "aarav.patel@khojai.in",
        "password": "SecurePassword123!",
        "full_name": "Aarav Patel",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    # Verify user profile returned
    user = data["user"]
    assert user["email"] == "aarav.patel@khojai.in"
    assert user["full_name"] == "Aarav Patel"
    assert user["role"] == "user"
    assert user["is_active"] is True

    # Critical security check: NEVER return password or password hash
    assert "password" not in user
    assert "hashed_password" not in user

    # Verify session cookie was set
    assert settings.COOKIE_NAME in response.cookies


@pytest.mark.asyncio
async def test_duplicate_registration(client: AsyncClient):
    """Test registering an existing email returns 409 Conflict."""
    payload = {
        "email": "duplicate.user@khojai.in",
        "password": "StrongPassword999!",
        "full_name": "First User",
    }
    # Initial registration
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    # Second registration with case variation
    duplicate_payload = {
        "email": "  DUPLICATE.USER@khojai.in  ",
        "password": "AnotherPassword123!",
        "full_name": "Second User",
    }
    res2 = await client.post("/api/v1/auth/register", json=duplicate_payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_successful_login(client: AsyncClient):
    """Test successful login returns access token and user metadata."""
    # Register user first
    reg_payload = {
        "email": "maya.sen@khojai.in",
        "password": "ExploreIndia2026!",
        "full_name": "Maya Sen",
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    # Log in
    login_payload = {
        "email": "maya.sen@khojai.in",
        "password": "ExploreIndia2026!",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "maya.sen@khojai.in"
    assert settings.COOKIE_NAME in response.cookies


@pytest.mark.asyncio
async def test_invalid_password(client: AsyncClient):
    """Test login with incorrect password returns 401 Unauthorized."""
    reg_payload = {
        "email": "kabir.mehta@khojai.in",
        "password": "CorrectPassword1!",
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {
        "email": "kabir.mehta@khojai.in",
        "password": "WrongPassword999!",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_invalid_token(client: AsyncClient):
    """Test accessing protected route with malformed or tampered token returns 401."""
    headers = {"Authorization": "Bearer not.a.valid.jwt.token"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert "Invalid or malformed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_expired_token(client: AsyncClient):
    """Test accessing protected route with expired token returns 401."""
    # Register a user
    reg_payload = {
        "email": "expired.test@khojai.in",
        "password": "Password123!",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    user_id = reg_res.json()["user"]["id"]

    # Generate an expired token (expires 1 hour in the past)
    expired_token = create_access_token(
        subject=user_id,
        email="expired.test@khojai.in",
        role="user",
        expires_delta=timedelta(hours=-1),
    )

    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_protected_endpoint_access(client: AsyncClient):
    """Test unauthenticated vs authenticated access to /auth/me."""
    # 1. Unauthenticated request -> 401
    res_unauth = await client.get("/api/v1/auth/me")
    assert res_unauth.status_code == 401

    # 2. Register user
    reg_payload = {
        "email": "me.test@khojai.in",
        "password": "Password1234!",
        "full_name": "Me Tester",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_res.json()["access_token"]

    # 3. Authenticated request via Authorization header -> 200
    headers = {"Authorization": f"Bearer {token}"}
    res_auth = await client.get("/api/v1/auth/me", headers=headers)
    assert res_auth.status_code == 200
    assert res_auth.json()["email"] == "me.test@khojai.in"
    assert res_auth.json()["full_name"] == "Me Tester"


@pytest.mark.asyncio
async def test_refresh_token_flow(client: AsyncClient):
    """Test token refresh using valid session cookie or body token."""
    reg_payload = {
        "email": "refresh.user@khojai.in",
        "password": "Password123!",
    }
    login_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert login_res.status_code == 201

    session_cookie = login_res.cookies.get(settings.COOKIE_NAME)
    assert session_cookie is not None

    # Perform refresh passing cookie
    client.cookies.set(settings.COOKIE_NAME, session_cookie)
    refresh_res = await client.post("/api/v1/auth/refresh")
    assert refresh_res.status_code == 200

    new_token = refresh_res.json()["access_token"]
    assert new_token is not None

    # Verify new token works on protected endpoint
    me_res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "refresh.user@khojai.in"


@pytest.mark.asyncio
async def test_logout_flow(client: AsyncClient):
    """Test logout revokes session and invalidates subsequent refreshes."""
    reg_payload = {
        "email": "logout.user@khojai.in",
        "password": "Password123!",
    }
    login_res = await client.post("/api/v1/auth/register", json=reg_payload)
    session_cookie = login_res.cookies.get(settings.COOKIE_NAME)

    client.cookies.set(settings.COOKIE_NAME, session_cookie)

    # Perform logout
    logout_res = await client.post("/api/v1/auth/logout")
    assert logout_res.status_code == 200
    assert logout_res.json()["ok"] is True

    # Verify cookie was cleared / expired in response
    # Attempting to refresh with the revoked session token must now fail
    client.cookies.set(settings.COOKIE_NAME, session_cookie)
    failed_refresh = await client.post("/api/v1/auth/refresh")
    assert failed_refresh.status_code == 401


@pytest.mark.asyncio
async def test_password_strength_validation(client: AsyncClient):
    """Test password strength validation errors on registration."""
    # Too short (< 8 chars)
    res_short = await client.post(
        "/api/v1/auth/register",
        json={"email": "short@khojai.in", "password": "abc"},
    )
    assert res_short.status_code == 422

    # No number
    res_no_num = await client.post(
        "/api/v1/auth/register",
        json={"email": "nonum@khojai.in", "password": "LettersOnlyHere!"},
    )
    assert res_no_num.status_code == 422
