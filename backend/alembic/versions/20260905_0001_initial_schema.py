"""Initial database schema for KHOJAI

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-05 22:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("bio", sa.String(length=500), nullable=True),
        sa.Column("theme_preference", sa.String(length=20), nullable=False, server_default="light"),
        sa.Column("travel_preferences", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_is_deleted", "users", ["is_deleted"])

    # 2. Create sessions table
    op.create_table(
        "sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("session_token", sa.String(length=255), nullable=False),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_id", "sessions", ["id"])
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_session_token", "sessions", ["session_token"], unique=True)
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])
    op.create_index("ix_sessions_is_revoked", "sessions", ["is_revoked"])

    # 3. Create destinations table
    op.create_table(
        "destinations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=150), nullable=False),
        sa.Column("best_season", sa.String(length=100), nullable=False),
        sa.Column("budget", sa.String(length=10), nullable=False),
        sa.Column("trust_score", sa.Integer(), nullable=False, server_default="85"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("accent_color", sa.String(length=20), nullable=False, server_default="#5d6b43"),
        sa.Column("coordinate_x", sa.String(length=20), nullable=False, server_default="50%"),
        sa.Column("coordinate_y", sa.String(length=20), nullable=False, server_default="50%"),
        sa.Column("demo_note", sa.Text(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("trust_score >= 0 AND trust_score <= 100", name="ck_destinations_trust_score"),
        sa.CheckConstraint("length(budget) >= 1 AND length(budget) <= 5", name="ck_destinations_budget"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_destinations_id", "destinations", ["id"])
    op.create_index("ix_destinations_slug", "destinations", ["slug"], unique=True)
    op.create_index("ix_destinations_name", "destinations", ["name"])
    op.create_index("ix_destinations_state", "destinations", ["state"])
    op.create_index("ix_destinations_region", "destinations", ["region"])
    op.create_index("ix_destinations_is_published", "destinations", ["is_published"])
    op.create_index("ix_destinations_is_featured", "destinations", ["is_featured"])
    op.create_index("ix_destinations_is_deleted", "destinations", ["is_deleted"])
    op.create_index("idx_destinations_filter", "destinations", ["region", "budget", "state"])

    # 4. Create destination_tags table
    op.create_table(
        "destination_tags",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("destination_id", sa.UUID(), nullable=False),
        sa.Column("tag", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_destination_tags_id", "destination_tags", ["id"])
    op.create_index("ix_destination_tags_destination_id", "destination_tags", ["destination_id"])
    op.create_index("ix_destination_tags_tag", "destination_tags", ["tag"])

    # 5. Create trust_metrics table
    op.create_table(
        "trust_metrics",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("destination_id", sa.UUID(), nullable=False),
        sa.Column("source_quality", sa.Integer(), nullable=False, server_default="85"),
        sa.Column("recency", sa.Integer(), nullable=False, server_default="85"),
        sa.Column("community_agreement", sa.Integer(), nullable=False, server_default="85"),
        sa.Column("completeness", sa.Integer(), nullable=False, server_default="85"),
        sa.Column("last_audited_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("source_quality >= 0 AND source_quality <= 100", name="ck_trust_source_quality"),
        sa.CheckConstraint("recency >= 0 AND recency <= 100", name="ck_trust_recency"),
        sa.CheckConstraint("community_agreement >= 0 AND community_agreement <= 100", name="ck_trust_community_agreement"),
        sa.CheckConstraint("completeness >= 0 AND completeness <= 100", name="ck_trust_completeness"),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("destination_id"),
    )
    op.create_index("ix_trust_metrics_id", "trust_metrics", ["id"])
    op.create_index("ix_trust_metrics_destination_id", "trust_metrics", ["destination_id"], unique=True)

    # 6. Create itineraries table
    op.create_table(
        "itineraries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("share_token", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("subtitle", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("total_budget", sa.String(length=100), nullable=False, server_default="15,000 / person"),
        sa.Column("preferences", sa.JSON(), nullable=False),
        sa.Column("primary_destination_id", sa.UUID(), nullable=True),
        sa.Column("match_score", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("rationale_bullets", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("match_score >= 0 AND match_score <= 100", name="ck_itinerary_match_score"),
        sa.ForeignKeyConstraint(["primary_destination_id"], ["destinations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_itineraries_id", "itineraries", ["id"])
    op.create_index("ix_itineraries_share_token", "itineraries", ["share_token"], unique=True)
    op.create_index("ix_itineraries_user_id", "itineraries", ["user_id"])
    op.create_index("ix_itineraries_primary_destination_id", "itineraries", ["primary_destination_id"])

    # 7. Create itinerary_days table
    op.create_table(
        "itinerary_days",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("itinerary_id", sa.UUID(), nullable=False),
        sa.Column("day_number", sa.String(length=10), nullable=False),
        sa.Column("place_name", sa.String(length=150), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("accent_color", sa.String(length=20), nullable=False, server_default="#5d6b43"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["itinerary_id"], ["itineraries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_itinerary_days_id", "itinerary_days", ["id"])
    op.create_index("ix_itinerary_days_itinerary_id", "itinerary_days", ["itinerary_id"])

    # 8. Create contributions table
    op.create_table(
        "contributions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("destination_id", sa.UUID(), nullable=True),
        sa.Column("place_name", sa.String(length=150), nullable=False),
        sa.Column("contributor_name", sa.String(length=150), nullable=True),
        sa.Column("story_text", sa.Text(), nullable=False),
        sa.Column("photo_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("moderation_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_contribution_status"),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contributions_id", "contributions", ["id"])
    op.create_index("ix_contributions_place_name", "contributions", ["place_name"])
    op.create_index("ix_contributions_status", "contributions", ["status"])
    op.create_index("ix_contributions_user_id", "contributions", ["user_id"])
    op.create_index("ix_contributions_destination_id", "contributions", ["destination_id"])

    # 9. Create community_stories table
    op.create_table(
        "community_stories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("destination_id", sa.UUID(), nullable=True),
        sa.Column("author_name", sa.String(length=150), nullable=False),
        sa.Column("author_role", sa.String(length=150), nullable=False),
        sa.Column("initials", sa.String(length=10), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("tag", sa.String(length=100), nullable=False, server_default="Local perspective"),
        sa.Column("time_display", sa.String(length=50), nullable=False, server_default="Recently"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_community_stories_id", "community_stories", ["id"])
    op.create_index("ix_community_stories_destination_id", "community_stories", ["destination_id"])
    op.create_index("ix_community_stories_is_active", "community_stories", ["is_active"])

    # 10. Create documents table
    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("document_type", sa.String(length=50), nullable=False, server_default="guide"),
        sa.Column("raw_content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_id", "documents", ["id"])
    op.create_index("ix_documents_title", "documents", ["title"])
    op.create_index("ix_documents_document_type", "documents", ["document_type"])

    # 11. Create document_chunks table
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("destination_id", sa.UUID(), nullable=True),
        sa.Column("chunk_content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("chunk_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_chunks_id", "document_chunks", ["id"])
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_destination_id", "document_chunks", ["destination_id"])


def downgrade() -> None:
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("community_stories")
    op.drop_table("contributions")
    op.drop_table("itinerary_days")
    op.drop_table("itineraries")
    op.drop_table("trust_metrics")
    op.drop_table("destination_tags")
    op.drop_table("destinations")
    op.drop_table("sessions")
    op.drop_table("users")
