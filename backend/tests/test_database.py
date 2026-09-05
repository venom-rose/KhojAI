import uuid
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.app.database.init_db import DESTINATIONS_SEED_DATA, seed_data
from backend.app.models import (
    CommunityStory,
    Contribution,
    Destination,
    DestinationTag,
    Document,
    DocumentChunk,
    Itinerary,
    ItineraryDay,
    Session,
    TrustMetric,
    User,
)


@pytest.mark.asyncio
async def test_destination_creation_and_relationships(db_session):
    """Test creating a Destination with 1:1 TrustMetric and 1:N DestinationTags."""
    dest = Destination(
        slug="ziro-test",
        name="Ziro Valley",
        state="Arunachal Pradesh",
        region="Northeast",
        category="Nature · Culture",
        best_season="Oct – Nov",
        budget="₹₹",
        trust_score=92,
        description="A beautiful valley in Arunachal.",
        image_url="/media/ziro.jpg",
        accent_color="#5d6b43",
        coordinate_x="71%",
        coordinate_y="24%",
        demo_note="Test note",
    )
    db_session.add(dest)
    await db_session.flush()

    # Add TrustMetric
    tm = TrustMetric(
        destination_id=dest.id,
        source_quality=95,
        recency=90,
        community_agreement=92,
        completeness=88,
    )
    db_session.add(tm)

    # Add Destination Tags
    tag1 = DestinationTag(destination_id=dest.id, tag="Slow travel")
    tag2 = DestinationTag(destination_id=dest.id, tag="Rice terraces")
    db_session.add_all([tag1, tag2])
    await db_session.commit()

    # Query back and verify
    result = await db_session.execute(select(Destination).where(Destination.slug == "ziro-test"))
    fetched_dest = result.scalars().first()

    assert fetched_dest is not None
    assert fetched_dest.name == "Ziro Valley"
    assert fetched_dest.trust_score == 92
    assert fetched_dest.is_deleted is False
    assert fetched_dest.created_at is not None

    # Verify relationships
    await db_session.refresh(fetched_dest, ["trust_metric", "tags"])
    assert fetched_dest.trust_metric is not None
    assert fetched_dest.trust_metric.source_quality == 95
    assert len(fetched_dest.tags) == 2
    assert {t.tag for t in fetched_dest.tags} == {"Slow travel", "Rice terraces"}


@pytest.mark.asyncio
async def test_destination_unique_slug_constraint(db_session):
    """Test that duplicate destination slugs raise an IntegrityError."""
    dest1 = Destination(
        slug="duplicate-slug",
        name="Place 1",
        state="State 1",
        region="Himalayas",
        category="Nature",
        best_season="Oct",
        budget="₹",
        trust_score=80,
        description="Desc 1",
        image_url="/img.jpg",
    )
    db_session.add(dest1)
    await db_session.commit()

    dest2 = Destination(
        slug="duplicate-slug",
        name="Place 2",
        state="State 2",
        region="South",
        category="Culture",
        best_season="Nov",
        budget="₹₹",
        trust_score=85,
        description="Desc 2",
        image_url="/img.jpg",
    )
    db_session.add(dest2)

    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_soft_delete_and_restore(db_session):
    """Test that soft deletion marks records without physical deletion."""
    dest = Destination(
        slug="soft-delete-test",
        name="Soft Delete Place",
        state="Himachal Pradesh",
        region="Himalayas",
        category="Outdoors",
        best_season="May",
        budget="₹₹",
        trust_score=88,
        description="Testing soft deletion",
        image_url="/img.jpg",
    )
    db_session.add(dest)
    await db_session.commit()

    assert dest.is_deleted is False
    assert dest.deleted_at is None

    # Perform soft delete
    dest.soft_delete()
    await db_session.commit()
    assert dest.is_deleted is True
    assert dest.deleted_at is not None

    # Restore
    dest.restore()
    await db_session.commit()
    assert dest.is_deleted is False
    assert dest.deleted_at is None


@pytest.mark.asyncio
async def test_itinerary_and_days_cascading(db_session):
    """Test that deleting an Itinerary cascades and removes its ItineraryDay items."""
    itinerary = Itinerary(
        share_token="test-share-123",
        title="5 Days in Tirthan",
        subtitle="Slow travel · 5 days",
        summary="A quiet loop through cedar forest.",
        total_budget="₹15,000 / person",
        preferences={"days": "5 days", "style": "Slow travel"},
        match_score=94,
        rationale_bullets=["Fits slow travel", "Within budget"],
    )
    db_session.add(itinerary)
    await db_session.flush()

    day1 = ItineraryDay(
        itinerary_id=itinerary.id,
        day_number="01",
        place_name="Tirthan Valley",
        title="Arrival",
        body="Walk by the river.",
        sort_order=1,
    )
    day2 = ItineraryDay(
        itinerary_id=itinerary.id,
        day_number="02",
        place_name="Gushaini",
        title="Forest Walk",
        body="Hike into cedar woods.",
        sort_order=2,
    )
    db_session.add_all([day1, day2])
    await db_session.commit()

    # Verify days are persisted
    days_result = await db_session.execute(
        select(ItineraryDay).where(ItineraryDay.itinerary_id == itinerary.id)
    )
    assert len(days_result.scalars().all()) == 2

    # Delete the parent itinerary
    await db_session.delete(itinerary)
    await db_session.commit()

    # Verify child days are deleted
    days_after_delete = await db_session.execute(
        select(ItineraryDay).where(ItineraryDay.itinerary_id == itinerary.id)
    )
    assert len(days_after_delete.scalars().all()) == 0


@pytest.mark.asyncio
async def test_user_and_session_validity(db_session):
    """Test User creation and Session expiration / validity properties."""
    user = User(
        email="traveler@khojai.in",
        hashed_password="hashed_test_password",
        full_name="Priya Sharma",
        role="user",
    )
    db_session.add(user)
    await db_session.flush()

    # Active valid session
    valid_session = Session(
        user_id=user.id,
        session_token="valid_token_xyz_123",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    # Expired session
    expired_session = Session(
        user_id=user.id,
        session_token="expired_token_abc_456",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )

    # Revoked session
    revoked_session = Session(
        user_id=user.id,
        session_token="revoked_token_def_789",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        is_revoked=True,
    )

    db_session.add_all([valid_session, expired_session, revoked_session])
    await db_session.commit()

    assert valid_session.is_valid is True
    assert valid_session.is_expired is False

    assert expired_session.is_valid is False
    assert expired_session.is_expired is True

    assert revoked_session.is_valid is False
    assert revoked_session.is_revoked is True


@pytest.mark.asyncio
async def test_contribution_lifecycle(db_session):
    """Test community field note contribution creation and status."""
    contribution = Contribution(
        place_name="Sangti Valley",
        contributor_name="Tenzin N.",
        story_text="A quiet valley near Dirang with black-necked cranes in winter.",
        status="pending",
    )
    db_session.add(contribution)
    await db_session.commit()

    assert contribution.id is not None
    assert contribution.status == "pending"
    assert contribution.reviewed_at is None

    # Approve the contribution
    contribution.status = "approved"
    contribution.reviewed_at = datetime.now(timezone.utc)
    contribution.moderation_notes = "Verified authentic local note."
    await db_session.commit()

    result = await db_session.execute(select(Contribution).where(Contribution.id == contribution.id))
    updated = result.scalars().first()
    assert updated.status == "approved"
    assert updated.reviewed_at is not None


@pytest.mark.asyncio
async def test_document_and_chunks_rag_structure(db_session):
    """Test RAG Document and DocumentChunk with vector embedding array."""
    doc = Document(
        title="Arunachal Pradesh Travel Advisory 2026",
        source_url="https://tourism.arunachal.gov.in",
        document_type="advisory",
        raw_content="Inner Line Permit (ILP) is required for domestic tourists visiting Ziro...",
    )
    db_session.add(doc)
    await db_session.flush()

    mock_embedding = [0.012, -0.045, 0.089, 0.123] * 192  # 768-dimensional mock vector
    chunk = DocumentChunk(
        document_id=doc.id,
        chunk_content="Inner Line Permit (ILP) details for Ziro...",
        embedding=mock_embedding,
        chunk_metadata={"region": "Northeast", "topic": "permit", "destination_slug": "ziro"},
    )
    db_session.add(chunk)
    await db_session.commit()

    result = await db_session.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc.id))
    fetched_chunk = result.scalars().first()

    assert fetched_chunk is not None
    assert len(fetched_chunk.embedding) == 768
    assert fetched_chunk.chunk_metadata["topic"] == "permit"


@pytest.mark.asyncio
async def test_seed_data_execution(db_session):
    """Test that seed_data successfully populates all 8 destinations and community stories."""
    await seed_data(db_session)

    # 1. Verify destinations count
    dest_result = await db_session.execute(select(Destination))
    destinations = dest_result.scalars().all()
    assert len(destinations) == len(DESTINATIONS_SEED_DATA)
    assert len(destinations) == 8

    # 2. Verify all slugs are present
    slugs = {d.slug for d in destinations}
    expected_slugs = {
        "ziro",
        "majuli",
        "tirthan-valley",
        "gandikota",
        "chopta",
        "orchha",
        "dzukou-valley",
        "gurez-valley",
    }
    assert slugs == expected_slugs

    # 3. Verify trust metrics were created for each destination
    tm_result = await db_session.execute(select(TrustMetric))
    trust_metrics = tm_result.scalars().all()
    assert len(trust_metrics) == 8

    # 4. Verify community stories
    stories_result = await db_session.execute(select(CommunityStory))
    stories = stories_result.scalars().all()
    assert len(stories) == 3
    authors = {s.author_name for s in stories}
    assert "Ananya R." in authors
    assert "Rohit M." in authors
    assert "Sonal K." in authors

    # 5. Verify admin user
    user_result = await db_session.execute(select(User).where(User.email == "admin@khojai.in"))
    admin = user_result.scalars().first()
    assert admin is not None
    assert admin.role == "admin"
