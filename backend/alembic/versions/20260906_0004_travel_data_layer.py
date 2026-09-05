"""Add complete scalable travel data layer

Revision ID: 0004_travel_data_layer
Revises: 0003_update_document_rag_fields
Create Date: 2026-09-06 01:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0004_travel_data_layer"
down_revision: Union[str, None] = "0003_update_document_rag_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. countries
    op.create_table(
        "countries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=2), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="INR", nullable=False),
        sa.Column("phone_code", sa.String(length=10), server_default="+91", nullable=True),
        sa.Column("continent", sa.String(length=50), server_default="Asia", nullable=False),
        sa.Column("source", sa.String(length=100), server_default="curated_editorial", nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_countries_id", "countries", ["id"])
    op.create_index("ix_countries_code", "countries", ["code"], unique=True)
    op.create_index("ix_countries_name", "countries", ["name"])
    op.create_index("idx_countries_code_name", "countries", ["code", "name"])
    op.create_index("idx_countries_provenance", "countries", ["source", "source_id"])

    # 2. states
    op.create_table(
        "states",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("country_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=True),
        sa.Column("region", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=100), server_default="curated_editorial", nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_states_id", "states", ["id"])
    op.create_index("ix_states_country_id", "states", ["country_id"])
    op.create_index("ix_states_name", "states", ["name"])
    op.create_index("ix_states_code", "states", ["code"])
    op.create_index("ix_states_region", "states", ["region"])
    op.create_index("idx_states_name_region", "states", ["name", "region"])
    op.create_index("idx_states_provenance", "states", ["source", "source_id"])

    # 3. cities
    op.create_table(
        "cities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("state_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("city_code", sa.String(length=10), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("elevation_meters", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=100), server_default="curated_editorial", nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["state_id"], ["states.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cities_id", "cities", ["id"])
    op.create_index("ix_cities_state_id", "cities", ["state_id"])
    op.create_index("ix_cities_name", "cities", ["name"])
    op.create_index("ix_cities_city_code", "cities", ["city_code"])
    op.create_index("idx_cities_name", "cities", ["name"])
    op.create_index("idx_cities_coordinates", "cities", ["latitude", "longitude"])
    op.create_index("idx_cities_provenance", "cities", ["source", "source_id"])

    # 4. destination_categories
    op.create_table(
        "destination_categories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon_name", sa.String(length=50), server_default="Compass", nullable=True),
        sa.Column("source", sa.String(length=100), server_default="curated_editorial", nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_destination_categories_id", "destination_categories", ["id"])
    op.create_index("ix_destination_categories_slug", "destination_categories", ["slug"], unique=True)
    op.create_index("idx_dest_categories_slug_name", "destination_categories", ["slug", "name"])
    op.create_index("idx_dest_categories_provenance", "destination_categories", ["source", "source_id"])

    # 5. Update destinations table with foreign keys, coordinates, and provenance
    with op.batch_alter_table("destinations") as batch_op:
        batch_op.add_column(sa.Column("country_id", sa.UUID(), nullable=True))
        batch_op.add_column(sa.Column("state_id", sa.UUID(), nullable=True))
        batch_op.add_column(sa.Column("city_id", sa.UUID(), nullable=True))
        batch_op.add_column(sa.Column("category_id", sa.UUID(), nullable=True))
        batch_op.add_column(sa.Column("latitude", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("longitude", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("is_hidden_gem", sa.Boolean(), server_default=sa.true(), nullable=False))
        batch_op.add_column(sa.Column("source", sa.String(length=100), server_default="curated_editorial", nullable=False))
        batch_op.add_column(sa.Column("source_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key("fk_destinations_country", "countries", ["country_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_destinations_state", "states", ["state_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_destinations_city", "cities", ["city_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_destinations_category", "destination_categories", ["category_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index("idx_destinations_name", ["name"])
        batch_op.create_index("idx_destinations_coordinates", ["latitude", "longitude"])
        batch_op.create_index("idx_destinations_geo_hierarchy", ["country_id", "state_id", "city_id"])
        batch_op.create_index("idx_destinations_provenance", ["source", "source_id"])

    # 6. airports
    op.create_table(
        "airports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("city_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("iata_code", sa.String(length=3), nullable=False),
        sa.Column("icao_code", sa.String(length=4), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("is_international", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("source", sa.String(length=100), server_default="curated_editorial", nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_airports_id", "airports", ["id"])
    op.create_index("ix_airports_city_id", "airports", ["city_id"])
    op.create_index("ix_airports_name", "airports", ["name"])
    op.create_index("ix_airports_iata_code", "airports", ["iata_code"], unique=True)
    op.create_index("idx_airports_iata", "airports", ["iata_code"])
    op.create_index("idx_airports_coordinates", "airports", ["latitude", "longitude"])
    op.create_index("idx_airports_provenance", "airports", ["source", "source_id"])

    # 7. seasons
    op.create_table(
        "seasons",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("destination_id", sa.UUID(), nullable=False),
        sa.Column("season_name", sa.String(length=50), nullable=False),
        sa.Column("start_month", sa.Integer(), nullable=False),
        sa.Column("end_month", sa.Integer(), nullable=False),
        sa.Column("weather_summary", sa.Text(), nullable=False),
        sa.Column("avg_temp_min_c", sa.Float(), nullable=True),
        sa.Column("avg_temp_max_c", sa.Float(), nullable=True),
        sa.Column("rainfall_level", sa.String(length=20), server_default="moderate", nullable=False),
        sa.Column("is_recommended", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("advisory_notes", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=100), server_default="curated_editorial", nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("start_month >= 1 AND start_month <= 12", name="ck_seasons_start_month"),
        sa.CheckConstraint("end_month >= 1 AND end_month <= 12", name="ck_seasons_end_month"),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_seasons_id", "seasons", ["id"])
    op.create_index("ix_seasons_destination_id", "seasons", ["destination_id"])
    op.create_index("idx_seasons_dest_rec", "seasons", ["destination_id", "is_recommended"])
    op.create_index("idx_seasons_provenance", "seasons", ["source", "source_id"])

    # 8. travel_tips
    op.create_table(
        "travel_tips",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("destination_id", sa.UUID(), nullable=False),
        sa.Column("category", sa.String(length=50), server_default="logistics", nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="1", nullable=False),
        sa.Column("source", sa.String(length=100), server_default="curated_editorial", nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_travel_tips_id", "travel_tips", ["id"])
    op.create_index("ix_travel_tips_destination_id", "travel_tips", ["destination_id"])
    op.create_index("idx_tips_dest_cat", "travel_tips", ["destination_id", "category"])
    op.create_index("idx_tips_provenance", "travel_tips", ["source", "source_id"])

    # 9. attractions
    op.create_table(
        "attractions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("destination_id", sa.UUID(), nullable=False),
        sa.Column("city_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("entry_fee", sa.String(length=50), server_default="Free", nullable=False),
        sa.Column("timings", sa.String(length=100), server_default="Sunrise to Sunset", nullable=False),
        sa.Column("difficulty", sa.String(length=30), server_default="Easy", nullable=False),
        sa.Column("recommended_duration_mins", sa.Integer(), server_default="120", nullable=False),
        sa.Column("tags", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("source", sa.String(length=100), server_default="curated_editorial", nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_attractions_id", "attractions", ["id"])
    op.create_index("ix_attractions_destination_id", "attractions", ["destination_id"])
    op.create_index("ix_attractions_city_id", "attractions", ["city_id"])
    op.create_index("ix_attractions_name", "attractions", ["name"])
    op.create_index("ix_attractions_category", "attractions", ["category"])
    op.create_index("idx_attractions_name_cat", "attractions", ["name", "category"])
    op.create_index("idx_attractions_coordinates", "attractions", ["latitude", "longitude"])
    op.create_index("idx_attractions_provenance", "attractions", ["source", "source_id"])

    # 10. activities
    op.create_table(
        "activities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("destination_id", sa.UUID(), nullable=False),
        sa.Column("city_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("activity_type", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("duration_hours", sa.Float(), server_default="2.5", nullable=False),
        sa.Column("price_range", sa.String(length=50), server_default="₹300 – ₹800", nullable=False),
        sa.Column("seasonality", sa.String(length=100), server_default="All year", nullable=False),
        sa.Column("guide_required", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("source", sa.String(length=100), server_default="curated_editorial", nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activities_id", "activities", ["id"])
    op.create_index("ix_activities_destination_id", "activities", ["destination_id"])
    op.create_index("ix_activities_city_id", "activities", ["city_id"])
    op.create_index("ix_activities_title", "activities", ["title"])
    op.create_index("ix_activities_activity_type", "activities", ["activity_type"])
    op.create_index("idx_activities_title_type", "activities", ["title", "activity_type"])
    op.create_index("idx_activities_provenance", "activities", ["source", "source_id"])

    # 11. hotels
    op.create_table(
        "hotels",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("destination_id", sa.UUID(), nullable=False),
        sa.Column("city_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("stay_type", sa.String(length=50), server_default="Homestay", nullable=False),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("price_per_night", sa.String(length=100), server_default="₹1,500 – ₹2,500", nullable=False),
        sa.Column("price_level", sa.String(length=5), server_default="₹₹", nullable=False),
        sa.Column("rating", sa.Float(), server_default="4.7", nullable=True),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column("contact_email", sa.String(length=100), nullable=True),
        sa.Column("booking_url", sa.String(length=500), nullable=True),
        sa.Column("amenities", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("sustainability_rating", sa.Integer(), server_default="90", nullable=False),
        sa.Column("source", sa.String(length=100), server_default="curated_editorial", nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("rating >= 0.0 AND rating <= 5.0", name="ck_hotels_rating"),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hotels_id", "hotels", ["id"])
    op.create_index("ix_hotels_destination_id", "hotels", ["destination_id"])
    op.create_index("ix_hotels_city_id", "hotels", ["city_id"])
    op.create_index("ix_hotels_name", "hotels", ["name"])
    op.create_index("ix_hotels_stay_type", "hotels", ["stay_type"])
    op.create_index("idx_hotels_name_type", "hotels", ["name", "stay_type"])
    op.create_index("idx_hotels_coordinates", "hotels", ["latitude", "longitude"])
    op.create_index("idx_hotels_provenance", "hotels", ["source", "source_id"])

    # 12. restaurants
    op.create_table(
        "restaurants",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("destination_id", sa.UUID(), nullable=False),
        sa.Column("city_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("cuisine_type", sa.String(length=100), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("price_range", sa.String(length=10), server_default="₹", nullable=False),
        sa.Column("rating", sa.Float(), server_default="4.5", nullable=True),
        sa.Column("must_try_dishes", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("opening_hours", sa.String(length=100), server_default="11:00 AM – 8:30 PM", nullable=False),
        sa.Column("source", sa.String(length=100), server_default="curated_editorial", nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("rating >= 0.0 AND rating <= 5.0", name="ck_restaurants_rating"),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_restaurants_id", "restaurants", ["id"])
    op.create_index("ix_restaurants_destination_id", "restaurants", ["destination_id"])
    op.create_index("ix_restaurants_city_id", "restaurants", ["city_id"])
    op.create_index("ix_restaurants_name", "restaurants", ["name"])
    op.create_index("ix_restaurants_cuisine_type", "restaurants", ["cuisine_type"])
    op.create_index("idx_restaurants_name_cuisine", "restaurants", ["name", "cuisine_type"])
    op.create_index("idx_restaurants_coordinates", "restaurants", ["latitude", "longitude"])
    op.create_index("idx_restaurants_provenance", "restaurants", ["source", "source_id"])

    # 13. transportation_options
    op.create_table(
        "transportation_options",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("destination_id", sa.UUID(), nullable=False),
        sa.Column("transport_type", sa.String(length=50), nullable=False),
        sa.Column("origin_name", sa.String(length=150), nullable=False),
        sa.Column("destination_name", sa.String(length=150), nullable=False),
        sa.Column("duration_hours", sa.Float(), nullable=False),
        sa.Column("cost_estimate", sa.String(length=100), nullable=False),
        sa.Column("frequency", sa.String(length=100), server_default="Daily", nullable=False),
        sa.Column("operator_name", sa.String(length=150), nullable=True),
        sa.Column("booking_tips", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=100), server_default="curated_editorial", nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transportation_options_id", "transportation_options", ["id"])
    op.create_index("ix_transportation_options_destination_id", "transportation_options", ["destination_id"])
    op.create_index("ix_transportation_options_transport_type", "transportation_options", ["transport_type"])
    op.create_index("idx_transport_dest_type", "transportation_options", ["destination_id", "transport_type"])
    op.create_index("idx_transport_provenance", "transportation_options", ["source", "source_id"])

    # 14. travel_routes
    op.create_table(
        "travel_routes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("destination_id", sa.UUID(), nullable=False),
        sa.Column("origin_city_id", sa.UUID(), nullable=True),
        sa.Column("route_name", sa.String(length=200), nullable=False),
        sa.Column("mode", sa.String(length=50), server_default="Road", nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.Column("typical_duration_hours", sa.Float(), nullable=False),
        sa.Column("road_condition", sa.String(length=100), server_default="Metalled two-lane highway with mountain curves", nullable=False),
        sa.Column("scenic_rating", sa.Integer(), server_default="9", nullable=False),
        sa.Column("seasonal_notes", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=100), server_default="curated_editorial", nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("scenic_rating >= 1 AND scenic_rating <= 10", name="ck_routes_scenic_rating"),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["origin_city_id"], ["cities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_travel_routes_id", "travel_routes", ["id"])
    op.create_index("ix_travel_routes_destination_id", "travel_routes", ["destination_id"])
    op.create_index("ix_travel_routes_origin_city_id", "travel_routes", ["origin_city_id"])
    op.create_index("ix_travel_routes_route_name", "travel_routes", ["route_name"])
    op.create_index("idx_routes_dest_mode", "travel_routes", ["destination_id", "mode"])
    op.create_index("idx_routes_provenance", "travel_routes", ["source", "source_id"])

    # 15. trips
    op.create_table(
        "trips",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("destination_id", sa.UUID(), nullable=True),
        sa.Column("share_token", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("total_days", sa.Integer(), server_default="5", nullable=False),
        sa.Column("budget_tier", sa.String(length=20), server_default="₹₹", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("is_public", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("total_days >= 1 AND total_days <= 60", name="ck_trips_total_days"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trips_id", "trips", ["id"])
    op.create_index("ix_trips_user_id", "trips", ["user_id"])
    op.create_index("ix_trips_destination_id", "trips", ["destination_id"])
    op.create_index("ix_trips_share_token", "trips", ["share_token"], unique=True)
    op.create_index("idx_trips_user_status", "trips", ["user_id", "status"])
    op.create_index("idx_trips_share_token", "trips", ["share_token"])

    # 16. trip_days
    op.create_table(
        "trip_days",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("trip_id", sa.UUID(), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("day_date", sa.Date(), nullable=True),
        sa.Column("theme_title", sa.String(length=200), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trip_days_id", "trip_days", ["id"])
    op.create_index("ix_trip_days_trip_id", "trip_days", ["trip_id"])
    op.create_index("idx_trip_days_trip_day", "trip_days", ["trip_id", "day_number"])

    # 17. trip_items
    op.create_table(
        "trip_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("trip_day_id", sa.UUID(), nullable=False),
        sa.Column("item_type", sa.String(length=30), nullable=False),
        sa.Column("attraction_id", sa.UUID(), nullable=True),
        sa.Column("hotel_id", sa.UUID(), nullable=True),
        sa.Column("restaurant_id", sa.UUID(), nullable=True),
        sa.Column("activity_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_time", sa.String(length=20), nullable=True),
        sa.Column("end_time", sa.String(length=20), nullable=True),
        sa.Column("estimated_cost", sa.String(length=50), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["trip_day_id"], ["trip_days.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["attraction_id"], ["attractions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["hotel_id"], ["hotels.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trip_items_id", "trip_items", ["id"])
    op.create_index("ix_trip_items_trip_day_id", "trip_items", ["trip_day_id"])
    op.create_index("ix_trip_items_attraction_id", "trip_items", ["attraction_id"])
    op.create_index("ix_trip_items_hotel_id", "trip_items", ["hotel_id"])
    op.create_index("ix_trip_items_restaurant_id", "trip_items", ["restaurant_id"])
    op.create_index("ix_trip_items_activity_id", "trip_items", ["activity_id"])
    op.create_index("idx_trip_items_day_order", "trip_items", ["trip_day_id", "sort_order"])

    # 18. user_travel_preferences
    op.create_table(
        "user_travel_preferences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("budget_preference", sa.String(length=10), server_default="₹₹", nullable=False),
        sa.Column("preferred_pace", sa.String(length=20), server_default="balanced", nullable=False),
        sa.Column("travel_styles", sa.JSON(), server_default='["Slow travel", "Culture-led"]', nullable=False),
        sa.Column("dietary_needs", sa.String(length=50), server_default="none", nullable=False),
        sa.Column("fitness_level", sa.String(length=30), server_default="moderate", nullable=False),
        sa.Column("preferred_stay_types", sa.JSON(), server_default='["Homestay", "Eco-Lodge"]', nullable=False),
        sa.Column("preferred_regions", sa.JSON(), server_default='["Himalayas", "Northeast"]', nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_travel_preferences_id", "user_travel_preferences", ["id"])
    op.create_index("ix_user_travel_preferences_user_id", "user_travel_preferences", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_table("user_travel_preferences")
    op.drop_table("trip_items")
    op.drop_table("trip_days")
    op.drop_table("trips")
    op.drop_table("travel_routes")
    op.drop_table("transportation_options")
    op.drop_table("restaurants")
    op.drop_table("hotels")
    op.drop_table("activities")
    op.drop_table("attractions")
    op.drop_table("travel_tips")
    op.drop_table("seasons")
    op.drop_table("airports")

    with op.batch_alter_table("destinations") as batch_op:
        batch_op.drop_index("idx_destinations_provenance")
        batch_op.drop_index("idx_destinations_geo_hierarchy")
        batch_op.drop_index("idx_destinations_coordinates")
        batch_op.drop_index("idx_destinations_name")
        batch_op.drop_constraint("fk_destinations_category", type_="foreignkey")
        batch_op.drop_constraint("fk_destinations_city", type_="foreignkey")
        batch_op.drop_constraint("fk_destinations_state", type_="foreignkey")
        batch_op.drop_constraint("fk_destinations_country", type_="foreignkey")
        batch_op.drop_column("last_synced_at")
        batch_op.drop_column("source_id")
        batch_op.drop_column("source")
        batch_op.drop_column("is_hidden_gem")
        batch_op.drop_column("longitude")
        batch_op.drop_column("latitude")
        batch_op.drop_column("category_id")
        batch_op.drop_column("city_id")
        batch_op.drop_column("state_id")
        batch_op.drop_column("country_id")

    op.drop_table("destination_categories")
    op.drop_table("cities")
    op.drop_table("states")
    op.drop_table("countries")
