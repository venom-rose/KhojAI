from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_optional_current_user
from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.schemas.search import (
    GlobalSearchOut,
    PaginatedConversationSearchOut,
    PaginatedDestinationSearchOut,
    PaginatedDocumentSearchOut,
)
from backend.app.security.rate_limiter import rate_limit_search
from backend.app.services.search_service import search_service

router = APIRouter(
    prefix="/search",
    tags=["Search & Discovery"],
    dependencies=[Depends(rate_limit_search)],
)


@router.get(
    "",
    response_model=GlobalSearchOut,
    summary="Global omnisearch",
    description="Search across destinations, indexed documents, and private conversation history.",
)
async def global_search(
    q: str = Query(..., min_length=1, max_length=200, description="Search term or inquiry"),
    limit: int = Query(default=5, ge=1, le=20, description="Max results per category"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    user_id = current_user.id if current_user else None
    return await search_service.global_search(
        db=db,
        q=q,
        user_id=user_id,
        limit_per_category=limit,
    )


@router.get(
    "/destinations",
    response_model=PaginatedDestinationSearchOut,
    summary="Search destinations with faceted filters",
    description="Faceted search matching the Discover page filters (region, state, budget, style, season, experience, sort).",
)
async def search_destinations(
    q: Optional[str] = Query(default=None, max_length=200, description="Destination keyword search"),
    region: Optional[str] = Query(default=None, description="Region filter, e.g. 'Northeast', 'Western Ghats'"),
    state: Optional[str] = Query(default=None, description="State filter, e.g. 'Arunachal Pradesh'"),
    budget: Optional[str] = Query(default=None, description="Budget tier: '₹', '₹₹', '₹₹₹'"),
    style: Optional[str] = Query(default=None, description="Travel style: 'Slow travel', 'Outdoors', 'Culture-led', 'Road trip'"),
    season: Optional[str] = Query(default=None, description="Optimal season: 'Oct – Feb', 'Mar – Jun', etc."),
    experience: Optional[str] = Query(default=None, description="Experience tag: 'Nature', 'Culture', 'Food', 'Outdoors', 'Heritage'"),
    sort: Optional[str] = Query(default="Recommended", description="Sort by: 'Recommended', 'Most Trusted', 'Recently Updated', 'Budget Friendly', 'Offbeat'"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    return await search_service.search_destinations(
        db=db,
        q=q,
        region=region,
        state=state,
        budget=budget,
        style=style,
        season=season,
        experience=experience,
        sort=sort,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/documents",
    response_model=PaginatedDocumentSearchOut,
    summary="Hybrid document search",
    description="Search documents combining keyword matching with semantic vector similarity.",
)
async def search_documents(
    q: str = Query(..., min_length=1, max_length=200, description="Search inquiry"),
    document_type: Optional[str] = Query(default=None, description="Filter by document type"),
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    min_similarity: float = Query(default=0.0, ge=0.0, le=1.0, description="Similarity threshold cutoff"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    user_id = current_user.id if current_user else None
    return await search_service.search_documents_hybrid(
        db=db,
        q=q,
        document_type=document_type,
        user_id=user_id,
        limit=limit,
        offset=offset,
        min_similarity=min_similarity,
    )


@router.get(
    "/conversations",
    response_model=PaginatedConversationSearchOut,
    summary="Search conversation history",
    description="Search user's conversation threads and individual dialogue messages.",
)
async def search_conversations(
    q: str = Query(..., min_length=1, max_length=200, description="Search inquiry"),
    is_pinned: Optional[bool] = Query(default=None, description="Filter pinned threads"),
    is_archived: Optional[bool] = Query(default=None, description="Filter archived threads"),
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    user_id = current_user.id if current_user else None
    return await search_service.search_conversations(
        db=db,
        q=q,
        user_id=user_id,
        is_pinned=is_pinned,
        is_archived=is_archived,
        limit=limit,
        offset=offset,
    )
