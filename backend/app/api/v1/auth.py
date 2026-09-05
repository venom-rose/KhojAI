from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user
from backend.app.config.settings import settings
from backend.app.database.session import get_db
from backend.app.models import User
from backend.app.schemas.auth import (
    MessageResponse,
    RefreshTokenIn,
    TokenResponse,
    UserLoginIn,
    UserOut,
    UserRegisterIn,
)
from backend.app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="Create a new user account with email and password, issuing an access token and session cookie.",
)
async def register(
    payload: UserRegisterIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user_agent = request.headers.get("user-agent")
    client_ip = request.client.host if request.client else None

    user, access_token, session_token = await auth_service.register_user(
        db=db,
        payload=payload,
        user_agent=user_agent,
        ip_address=client_ip,
    )

    # Set HTTP-only secure session cookie matching frontend shared/const.ts COOKIE_NAME
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=session_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAME_SITE,
        path="/",
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user",
    description="Authenticate with email and password to receive an access token and persistent session cookie.",
)
async def login(
    payload: UserLoginIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user_agent = request.headers.get("user-agent")
    client_ip = request.client.host if request.client else None

    user, access_token, session_token = await auth_service.authenticate_user(
        db=db,
        payload=payload,
        user_agent=user_agent,
        ip_address=client_ip,
    )

    # Set HTTP-only secure session cookie
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=session_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAME_SITE,
        path="/",
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Exchange a valid session token (from HTTP-only cookie or request body) for a fresh access token.",
)
async def refresh_token(
    request: Request,
    payload: RefreshTokenIn = RefreshTokenIn(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    # Check body first, then fallback to cookie
    session_token = payload.refresh_token or request.cookies.get(settings.COOKIE_NAME)

    user, new_access_token = await auth_service.refresh_session(
        db=db,
        session_token=session_token,
    )

    return TokenResponse(
        access_token=new_access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Log out user",
    description="Revoke the active session in the database and clear the session cookie.",
)
async def logout(
    request: Request,
    response: Response,
    payload: RefreshTokenIn = RefreshTokenIn(),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    session_token = payload.refresh_token or request.cookies.get(settings.COOKIE_NAME)

    await auth_service.logout_session(db=db, session_token=session_token)

    # Delete session cookie
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAME_SITE,
    )

    return MessageResponse(
        ok=True,
        message="Successfully logged out.",
    )


@router.get(
    "/me",
    response_model=UserOut,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="Protected endpoint returning the profile of the currently authenticated user.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserOut:
    return UserOut.model_validate(current_user)
