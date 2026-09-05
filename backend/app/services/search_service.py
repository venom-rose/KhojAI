import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.destination import Destination, DestinationTag
from backend.app.models.document import Document, DocumentChunk
from backend.app.models.chat import Conversation, ChatMessage
from backend.app.rag.embeddings import compute_cosine_similarity, get_embedding_provider
from backend.app.schemas.search import (
    ConversationSearchResultItem,
    DestinationSearchResultItem,
    DocumentSearchResultItem,
    GlobalSearchOut,
    PaginatedConversationSearchOut,
    PaginatedDestinationSearchOut,
    PaginatedDocumentSearchOut,
)

logger = logging.getLogger(__name__)


class SearchService:
    """Service providing unified keyword, semantic vector, and hybrid search capabilities."""

    def __init__(self):
        self._embedding_provider = None

    @property
    def embedding_provider(self):
        if self._embedding_provider is None:
            self._embedding_provider = get_embedding_provider()
        return self._embedding_provider

    async def search_destinations(
        self,
        db: AsyncSession,
        q: Optional[str] = None,
        region: Optional[str] = None,
        state: Optional[str] = None,
        budget: Optional[str] = None,
        style: Optional[str] = None,
        season: Optional[str] = None,
        experience: Optional[str] = None,
        sort: Optional[str] = "Recommended",
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedDestinationSearchOut:
        """Faceted search across destinations matching the KhojAI Discover interface."""
        conditions = [Destination.is_deleted.is_(False)]

        # 1. Text Query Filter
        clean_q = q.strip() if q and q.strip() else None
        if clean_q:
            term = f"%{clean_q}%"
            conditions.append(
                or_(
                    Destination.name.ilike(term),
                    Destination.state.ilike(term),
                    Destination.region.ilike(term),
                    Destination.category.ilike(term),
                    Destination.description.ilike(term),
                )
            )

        # 2. Refinement Filters
        if region and region != "All regions":
            conditions.append(Destination.region.ilike(region.strip()))
        if state and state != "All states":
            conditions.append(Destination.state.ilike(state.strip()))
        if budget and budget != "Any budget":
            conditions.append(Destination.budget == budget.strip())
        if season and season != "Any season":
            conditions.append(Destination.best_season.ilike(f"%{season.strip()}%"))
        if style and style != "Any style":
            style_term = f"%{style.replace(' travel', '').strip()}%"
            conditions.append(
                or_(
                    Destination.category.ilike(style_term),
                    Destination.tags.any(DestinationTag.tag.ilike(style_term)),
                )
            )
        if experience and experience != "Any experience":
            exp_term = f"%{experience.strip()}%"
            conditions.append(
                or_(
                    Destination.category.ilike(exp_term),
                    Destination.tags.any(DestinationTag.tag.ilike(exp_term)),
                )
            )

        # 3. Base Query
        stmt = (
            select(Destination)
            .options(selectinload(Destination.tags))
            .where(*conditions)
            .distinct()
        )

        # 4. Sorting
        sort_choice = sort or "Recommended"
        if sort_choice == "Most Trusted":
            stmt = stmt.order_by(desc(Destination.trust_score))
        elif sort_choice == "Recently Updated":
            stmt = stmt.order_by(desc(Destination.updated_at))
        elif sort_choice == "Budget Friendly":
            stmt = stmt.order_by(func.length(Destination.budget).asc())
        elif sort_choice == "Offbeat":
            stmt = stmt.order_by(Destination.trust_score.asc())
        else:
            # "Recommended" default
            stmt = stmt.order_by(desc(Destination.trust_score), desc(Destination.created_at))

        # Total Count
        count_stmt = select(func.count(func.distinct(Destination.id))).where(*conditions)
        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one()

        # Paginated fetch
        paginated_stmt = stmt.limit(limit).offset(offset)
        result = await db.execute(paginated_stmt)
        destinations = result.scalars().all()

        items = []
        for dest in destinations:
            # Relevance scoring for search ranking
            relevance = 1.0
            if clean_q:
                q_low = clean_q.lower()
                name_low = dest.name.lower()
                if q_low == name_low:
                    relevance = 1.0
                elif name_low.startswith(q_low):
                    relevance = 0.9
                elif q_low in name_low:
                    relevance = 0.8
                elif q_low in dest.category.lower():
                    relevance = 0.6
                else:
                    relevance = 0.4

            items.append(
                DestinationSearchResultItem(
                    id=dest.id,
                    slug=dest.slug,
                    name=dest.name,
                    state=dest.state,
                    region=dest.region,
                    category=dest.category,
                    best_season=dest.best_season,
                    budget=dest.budget,
                    trust_score=dest.trust_score,
                    description=dest.description,
                    image_url=dest.image_url,
                    accent_color=dest.accent_color,
                    tags=[t.tag for t in dest.tags] if dest.tags else [],
                    relevance_score=relevance,
                )
            )

        if clean_q and sort_choice == "Recommended":
            items.sort(key=lambda x: (x.relevance_score, x.trust_score), reverse=True)

        return PaginatedDestinationSearchOut(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def search_documents_hybrid(
        self,
        db: AsyncSession,
        q: str,
        document_type: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
        limit: int = 10,
        offset: int = 0,
        min_similarity: float = 0.0,
    ) -> PaginatedDocumentSearchOut:
        """Hybrid search across documents combining keyword matching and semantic vector similarity."""
        clean_q = q.strip()
        if not clean_q:
            return PaginatedDocumentSearchOut(items=[], total=0, limit=limit, offset=offset)

        # 1. Compute query embedding
        query_vector = await self.embedding_provider.embed_text(clean_q)

        # 2. Query candidates with ownership and status constraints
        conditions = [Document.status == "ready"]
        if user_id is not None:
            conditions.append(or_(Document.user_id == user_id, Document.user_id.is_(None)))
        else:
            # Anonymous search: strictly limited to public system documents
            conditions.append(Document.user_id.is_(None))
        if document_type:
            conditions.append(Document.document_type == document_type)

        stmt = (
            select(DocumentChunk, Document.title, Document.document_type, Document.source_url)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(*conditions)
        )
        result = await db.execute(stmt)
        candidates = result.all()

        scored_items = []
        q_lower = clean_q.lower()

        for chunk, doc_title, doc_type, source_url in candidates:
            # 3. Vector Similarity
            vector_sim = 0.0
            if chunk.embedding:
                vector_sim = compute_cosine_similarity(query_vector, chunk.embedding)

            # 4. Keyword Score
            keyword_score = 0.0
            content_lower = chunk.chunk_content.lower()
            title_lower = doc_title.lower()

            if q_lower in title_lower:
                keyword_score = max(keyword_score, 0.9)
            if q_lower in content_lower:
                keyword_score = max(keyword_score, 0.7)
            # Word token overlap
            q_words = set(q_lower.split())
            if q_words:
                overlap = sum(1 for w in q_words if w in content_lower)
                overlap_ratio = overlap / len(q_words)
                keyword_score = max(keyword_score, overlap_ratio * 0.5)

            # 5. Hybrid Combined Score (50% vector + 50% keyword)
            hybrid_score = (0.5 * vector_sim) + (0.5 * keyword_score)

            if hybrid_score >= min_similarity or vector_sim >= 0.15 or keyword_score >= 0.5:
                scored_items.append((
                    hybrid_score,
                    vector_sim,
                    DocumentSearchResultItem(
                        chunk_id=chunk.id,
                        document_id=chunk.document_id,
                        document_title=doc_title,
                        document_type=doc_type,
                        content=chunk.chunk_content,
                        similarity=round(vector_sim, 4),
                        relevance_score=round(hybrid_score, 4),
                        source_url=source_url,
                        metadata=chunk.chunk_metadata,
                    )
                ))

        # 6. Sort descending by hybrid relevance score
        scored_items.sort(key=lambda x: x[0], reverse=True)
        total = len(scored_items)

        paginated = [item[2] for item in scored_items[offset : offset + limit]]

        return PaginatedDocumentSearchOut(
            items=paginated,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def search_conversations(
        self,
        db: AsyncSession,
        q: str,
        user_id: Optional[uuid.UUID] = None,
        is_pinned: Optional[bool] = None,
        is_archived: Optional[bool] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> PaginatedConversationSearchOut:
        """Search conversations and messages scoped strictly to user ownership."""
        clean_q = q.strip()
        if not clean_q:
            return PaginatedConversationSearchOut(items=[], total=0, limit=limit, offset=offset)

        conditions = []
        if user_id is not None:
            conditions.append(Conversation.user_id == user_id)
        else:
            # Anonymous search: strictly limited to unassigned/anonymous sessions
            conditions.append(Conversation.user_id.is_(None))
        if is_pinned is not None:
            conditions.append(Conversation.is_pinned == is_pinned)
        if is_archived is not None:
            conditions.append(Conversation.is_archived == is_archived)

        term = f"%{clean_q}%"
        # Match conversation title/summary OR child message content
        message_match = select(ChatMessage.content).where(
            and_(
                ChatMessage.conversation_id == Conversation.id,
                ChatMessage.content.ilike(term),
            )
        ).limit(1).scalar_subquery()

        query_filter = or_(
            Conversation.title.ilike(term),
            Conversation.summary.ilike(term),
            Conversation.messages.any(ChatMessage.content.ilike(term)),
        )
        conditions.append(query_filter)

        stmt = (
            select(Conversation, message_match.label("matched_content"))
            .where(*conditions)
            .order_by(desc(Conversation.is_pinned), desc(Conversation.updated_at))
        )

        count_stmt = select(func.count(Conversation.id)).where(*conditions)
        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one()

        paginated_stmt = stmt.limit(limit).offset(offset)
        result = await db.execute(paginated_stmt)
        rows = result.all()

        items = []
        q_low = clean_q.lower()
        for conv, matched_content in rows:
            relevance = 0.5
            if q_low in conv.title.lower():
                relevance = 1.0
            elif matched_content and q_low in matched_content.lower():
                relevance = 0.7

            snippet = matched_content
            if snippet and len(snippet) > 150:
                snippet = snippet[:150] + "..."

            items.append(
                ConversationSearchResultItem(
                    conversation_id=conv.id,
                    title=conv.title,
                    summary=conv.summary,
                    model=conv.model,
                    matched_message=snippet,
                    is_pinned=conv.is_pinned,
                    is_archived=conv.is_archived,
                    relevance_score=relevance,
                    updated_at=conv.updated_at,
                )
            )

        return PaginatedConversationSearchOut(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def global_search(
        self,
        db: AsyncSession,
        q: str,
        user_id: Optional[uuid.UUID] = None,
        limit_per_category: int = 5,
    ) -> GlobalSearchOut:
        """Omnisearch across destinations, knowledge documents, and user conversations."""
        clean_q = q.strip()
        if not clean_q:
            return GlobalSearchOut(query="", total_hits=0)

        # Run category searches
        dest_res = await self.search_destinations(
            db=db, q=clean_q, limit=limit_per_category, offset=0
        )
        doc_res = await self.search_documents_hybrid(
            db=db, q=clean_q, user_id=user_id, limit=limit_per_category, offset=0
        )
        conv_res = await self.search_conversations(
            db=db, q=clean_q, user_id=user_id, limit=limit_per_category, offset=0
        )

        total_hits = dest_res.total + doc_res.total + conv_res.total

        return GlobalSearchOut(
            query=clean_q,
            destinations=dest_res.items,
            documents=doc_res.items,
            conversations=conv_res.items,
            total_hits=total_hits,
        )


search_service = SearchService()
