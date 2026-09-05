from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config.settings import settings
from backend.app.models import Session as UserSession, User
from backend.app.schemas.auth import UserLoginIn, UserRegisterIn
from backend.app.security.jwt import (
    create_access_token,
    generate_session_token,
)
from backend.app.security.password import hash_password, verify_password


class AuthService:
    """Service handling user registration, authentication, token rotation, and sessions."""

    @staticmethod
    async def register_user(
        db: AsyncSession,
        payload: UserRegisterIn,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Tuple[User, str, str]:
        """Register a new user account, hash password, and issue initial session.

        Raises:
            HTTPException 409: If email is already registered.
        """
        normalized_email = payload.email.strip().lower()

        # Check for existing user
        result = await db.execute(select(User).where(User.email == normalized_email))
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email address already exists.",
            )

        # Hash password and create user
        hashed = hash_password(payload.password)
        user = User(
            email=normalized_email,
            hashed_password=hashed,
            full_name=payload.full_name.strip() if payload.full_name else None,
            role="user",
            is_active=True,
            is_verified=False,
        )
        db.add(user)
        await db.flush()

        # Issue access token and persistent session
        access_token, session_token = await AuthService._create_session_tokens(
            db, user, user_agent=user_agent, ip_address=ip_address
        )
        await db.commit()
        await db.refresh(user)

        return user, access_token, session_token

    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        payload: UserLoginIn,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Tuple[User, str, str]:
        """Verify user credentials and create an authenticated session.

        Raises:
            HTTPException 401: For invalid credentials or inactive account.
        """
        normalized_email = payload.email.strip().lower()

        result = await db.execute(
            select(User).where(User.email == normalized_email, User.is_deleted == False)
        )
        user = result.scalars().first()

        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been deactivated. Please contact support.",
            )

        # Issue access token and persistent session
        access_token, session_token = await AuthService._create_session_tokens(
            db, user, user_agent=user_agent, ip_address=ip_address
        )
        await db.commit()
        await db.refresh(user)

        return user, access_token, session_token

    @staticmethod
    async def refresh_session(
        db: AsyncSession,
        session_token: Optional[str],
    ) -> Tuple[User, str]:
        """Verify refresh session token and issue a fresh access token.

        Raises:
            HTTPException 401: If token is missing, expired, or revoked.
        """
        if not session_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh session token is required.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        result = await db.execute(
            select(UserSession).where(UserSession.session_token == session_token)
        )
        session_obj = result.scalars().first()

        if not session_obj or not session_obj.is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has expired or been revoked. Please sign in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Load user
        user_result = await db.execute(
            select(User).where(User.id == session_obj.user_id, User.is_deleted == False)
        )
        user = user_result.scalars().first()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is no longer active.",
            )

        access_token = create_access_token(
            subject=user.id,
            email=user.email,
            role=user.role,
        )

        return user, access_token

    @staticmethod
    async def logout_session(db: AsyncSession, session_token: Optional[str]) -> bool:
        """Revoke the active session."""
        if not session_token:
            return True

        result = await db.execute(
            select(UserSession).where(UserSession.session_token == session_token)
        )
        session_obj = result.scalars().first()

        if session_obj:
            session_obj.is_revoked = True
            await db.commit()

        return True

    @staticmethod
    async def _create_session_tokens(
        db: AsyncSession,
        user: User,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Internal helper to generate JWT access token and persist Session record."""
        access_token = create_access_token(
            subject=user.id,
            email=user.email,
            role=user.role,
        )

        session_token = generate_session_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        new_session = UserSession(
            user_id=user.id,
            session_token=session_token,
            user_agent=user_agent[:500] if user_agent else None,
            ip_address=ip_address[:45] if ip_address else None,
            expires_at=expires_at,
            is_revoked=False,
        )
        db.add(new_session)

        return access_token, session_token


auth_service = AuthService()
