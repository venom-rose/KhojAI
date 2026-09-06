import asyncio
import logging
import uuid
from datetime import datetime, timezone
import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config.settings import settings
from backend.app.database.base import Base
from backend.app.database.session import AsyncSessionFactory, engine
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("khojai.init_db")

# Seed data extracted directly from client/src/data/destinations.ts
DESTINATIONS_SEED_DATA = [
    {
        "slug": "ziro",
        "name": "Ziro",
        "state": "Arunachal Pradesh",
        "region": "Northeast",
        "category": "Nature · Culture",
        "tags": ["Slow travel", "Rice terraces", "Local food"],
        "best_season": "Oct – Nov",
        "budget": "₹₹",
        "trust_score": 92,
        "description": "A valley of emerald terraces, warm community stays and music that travels further than the road in.",
        "image_url": "/images/ziro-valley.jpg",
        "accent_color": "#5d6b43",
        "coordinate_x": "71%",
        "coordinate_y": "24%",
        "demo_note": "Illustrative demo content for MVP review; not a live travel advisory.",
        "is_featured": True,
        "trust_metrics": {
            "source_quality": 94,
            "recency": 89,
            "community_agreement": 93,
            "completeness": 91,
        },
    },
    {
        "slug": "majuli",
        "name": "Majuli",
        "state": "Assam",
        "region": "Northeast",
        "category": "River · Culture",
        "tags": ["Island life", "Satras", "Cycling"],
        "best_season": "Nov – Feb",
        "budget": "₹",
        "trust_score": 88,
        "description": "Move slowly through river-island life, where workshops, wetlands and long afternoons share the same horizon.",
        "image_url": "/images/majuli-island.jpg",
        "accent_color": "#b8734a",
        "coordinate_x": "67%",
        "coordinate_y": "30%",
        "demo_note": "Illustrative demo content for MVP review; not a live travel advisory.",
        "is_featured": True,
        "trust_metrics": {
            "source_quality": 88,
            "recency": 86,
            "community_agreement": 90,
            "completeness": 84,
        },
    },
    {
        "slug": "tirthan-valley",
        "name": "Tirthan Valley",
        "state": "Himachal Pradesh",
        "region": "Himalayas",
        "category": "Forest · Outdoors",
        "tags": ["River walks", "Cedar forest", "Cabin stays"],
        "best_season": "Mar – Jun",
        "budget": "₹₹",
        "trust_score": 90,
        "description": "A forest-fringed river corridor for long walks, clear water and the luxury of a quieter morning.",
        "image_url": "/images/tirthan-valley.jpg",
        "accent_color": "#34584d",
        "coordinate_x": "40%",
        "coordinate_y": "16%",
        "demo_note": "Illustrative demo content for MVP review; not a live travel advisory.",
        "is_featured": True,
        "trust_metrics": {
            "source_quality": 91,
            "recency": 90,
            "community_agreement": 89,
            "completeness": 90,
        },
    },
    {
        "slug": "gandikota",
        "name": "Gandikota",
        "state": "Andhra Pradesh",
        "region": "South",
        "category": "Landscape · History",
        "tags": ["Red gorge", "Sunrise", "Road trip"],
        "best_season": "Oct – Feb",
        "budget": "₹",
        "trust_score": 84,
        "description": "Terracotta cliffs, a river folded below and a horizon that makes the road feel like part of the destination.",
        "image_url": "/images/gandikota-canyon.jpg",
        "accent_color": "#b65c3d",
        "coordinate_x": "47%",
        "coordinate_y": "60%",
        "demo_note": "Illustrative demo content for MVP review; not a live travel advisory.",
        "is_featured": True,
        "trust_metrics": {
            "source_quality": 84,
            "recency": 82,
            "community_agreement": 86,
            "completeness": 83,
        },
    },
    {
        "slug": "chopta",
        "name": "Chopta",
        "state": "Uttarakhand",
        "region": "Himalayas",
        "category": "Meadows · Trek",
        "tags": ["Alpine trails", "Birding", "Sunrise"],
        "best_season": "Apr – Jun",
        "budget": "₹₹",
        "trust_score": 87,
        "description": "A small base for big skies, alpine walks and mountain mornings that begin before the rest of the valley.",
        "image_url": "/images/chopta-meadows.jpg",
        "accent_color": "#72885c",
        "coordinate_x": "42%",
        "coordinate_y": "22%",
        "demo_note": "Illustrative demo content for MVP review; not a live travel advisory.",
        "is_featured": False,
        "trust_metrics": {
            "source_quality": 87,
            "recency": 85,
            "community_agreement": 88,
            "completeness": 86,
        },
    },
    {
        "slug": "orchha",
        "name": "Orchha",
        "state": "Madhya Pradesh",
        "region": "Central India",
        "category": "Heritage · Slow travel",
        "tags": ["Riverside ruins", "Craft", "Architecture"],
        "best_season": "Oct – Mar",
        "budget": "₹",
        "trust_score": 86,
        "description": "A river, a ruined palace skyline and enough unhurried corners to make history feel close at hand.",
        "image_url": "/images/orchha-palace.jpg",
        "accent_color": "#a37c55",
        "coordinate_x": "39%",
        "coordinate_y": "43%",
        "demo_note": "Illustrative demo content for MVP review; not a live travel advisory.",
        "is_featured": False,
        "trust_metrics": {
            "source_quality": 86,
            "recency": 88,
            "community_agreement": 84,
            "completeness": 85,
        },
    },
    {
        "slug": "dzukou-valley",
        "name": "Dzukou Valley",
        "state": "Nagaland",
        "region": "Northeast",
        "category": "Trek · Wildflowers",
        "tags": ["High valley", "Seasonal bloom", "Trekking"],
        "best_season": "Jun – Sep",
        "budget": "₹₹",
        "trust_score": 89,
        "description": "A high valley of soft ridgelines and seasonal colour, reached one patient step at a time.",
        "image_url": "/images/dzukou-valley.jpg",
        "accent_color": "#9b6d3d",
        "coordinate_x": "72%",
        "coordinate_y": "34%",
        "demo_note": "Illustrative demo content for MVP review; not a live travel advisory.",
        "is_featured": False,
        "trust_metrics": {
            "source_quality": 90,
            "recency": 87,
            "community_agreement": 91,
            "completeness": 87,
        },
    },
    {
        "slug": "gurez-valley",
        "name": "Gurez Valley",
        "state": "Jammu & Kashmir",
        "region": "Himalayas",
        "category": "Mountains · Culture",
        "tags": ["Wooden homes", "High valley", "Community stays"],
        "best_season": "May – Sep",
        "budget": "₹₹₹",
        "trust_score": 83,
        "description": "A high-altitude valley where wooden homes, sharp peaks and generous local stories set the pace.",
        "image_url": "/images/gurez-valley.jpg",
        "accent_color": "#48677b",
        "coordinate_x": "29%",
        "coordinate_y": "9%",
        "demo_note": "Illustrative demo content for MVP review; not a live travel advisory.",
        "is_featured": False,
        "trust_metrics": {
            "source_quality": 82,
            "recency": 80,
            "community_agreement": 87,
            "completeness": 81,
        },
    },
]

COMMUNITY_STORIES_SEED = [
    {
        "author_name": "Ananya R.",
        "author_role": "Local guide · Ziro",
        "quote": "The best part of Ziro is not a single viewpoint. It is the way the valley makes you slow down.",
        "tag": "Local perspective",
        "time_display": "2 days ago",
        "initials": "AR",
        "display_order": 1,
    },
    {
        "author_name": "Rohit M.",
        "author_role": "Weekend explorer · Pune",
        "quote": "Majuli felt like pressing pause. We planned less and noticed more.",
        "tag": "Recent stay",
        "time_display": "1 week ago",
        "initials": "RM",
        "display_order": 2,
    },
    {
        "author_name": "Sonal K.",
        "author_role": "Food researcher · Delhi",
        "quote": "The signal I trust most is when several different travellers notice the same generous detail.",
        "tag": "Trust note",
        "time_display": "2 weeks ago",
        "initials": "SK",
        "display_order": 3,
    },
]


async def init_db(drop_all: bool = False) -> None:
    """Initialize database tables and seed authentic destination data."""
    logger.info("Initializing database...")

    async with engine.begin() as conn:
        if drop_all:
            logger.warning("Dropping all existing database tables...")
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Creating tables according to SQLAlchemy Base metadata...")
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionFactory() as session:
        await seed_data(session)

    logger.info("Database initialization completed successfully.")


async def seed_data(session: AsyncSession) -> None:
    """Seed default administrative user, destinations, trust metrics, and community stories."""
    # 1. Seed Demo Admin User
    admin_result = await session.execute(select(User).where(User.email == "admin@khojai.in"))
    admin_user = admin_result.scalars().first()

    if not admin_user:
        hashed_pw = bcrypt.hashpw("Admin@KhojAI2026".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        admin_user = User(
            email="admin@khojai.in",
            hashed_password=hashed_pw,
            full_name="KHOJAI Administrator",
            role="admin",
            is_active=True,
            is_verified=True,
        )
        session.add(admin_user)
        logger.info("Seeded admin user: admin@khojai.in")

    # 2. Seed Verified Destinations
    for dest_data in DESTINATIONS_SEED_DATA:
        result = await session.execute(select(Destination).where(Destination.slug == dest_data["slug"]))
        existing_dest = result.scalars().first()

        if not existing_dest:
            destination = Destination(
                slug=dest_data["slug"],
                name=dest_data["name"],
                state=dest_data["state"],
                region=dest_data["region"],
                category=dest_data["category"],
                best_season=dest_data["best_season"],
                budget=dest_data["budget"],
                trust_score=dest_data["trust_score"],
                description=dest_data["description"],
                image_url=dest_data["image_url"],
                accent_color=dest_data["accent_color"],
                coordinate_x=dest_data["coordinate_x"],
                coordinate_y=dest_data["coordinate_y"],
                demo_note=dest_data["demo_note"],
                is_featured=dest_data["is_featured"],
                is_published=True,
            )
            session.add(destination)
            await session.flush()

            # Add Destination Tags
            for tag_str in dest_data["tags"]:
                tag = DestinationTag(destination_id=destination.id, tag=tag_str)
                session.add(tag)

            # Add Trust Metrics
            tm_data = dest_data["trust_metrics"]
            trust_metric = TrustMetric(
                destination_id=destination.id,
                source_quality=tm_data["source_quality"],
                recency=tm_data["recency"],
                community_agreement=tm_data["community_agreement"],
                completeness=tm_data["completeness"],
                last_audited_at=datetime.now(timezone.utc),
            )
            session.add(trust_metric)
            logger.info(f"Seeded destination: {destination.name} ({destination.slug})")

    # 3. Seed Community Stories
    for story_data in COMMUNITY_STORIES_SEED:
        result = await session.execute(
            select(CommunityStory).where(CommunityStory.author_name == story_data["author_name"])
        )
        existing_story = result.scalars().first()

        if not existing_story:
            story = CommunityStory(
                author_name=story_data["author_name"],
                author_role=story_data["author_role"],
                initials=story_data["initials"],
                quote=story_data["quote"],
                tag=story_data["tag"],
                time_display=story_data["time_display"],
                display_order=story_data["display_order"],
                is_active=True,
            )
            session.add(story)
            logger.info(f"Seeded community story by: {story.author_name}")

    await session.commit()


if __name__ == "__main__":
    asyncio.run(init_db())
