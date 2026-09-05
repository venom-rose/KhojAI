"""Update documents and document_chunks tables with RAG pipeline fields

Revision ID: 0003_update_document_rag_fields
Revises: 0002_add_chat_tables
Create Date: 2026-09-05 23:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "0003_update_document_rag_fields"
down_revision: Union[str, None] = "0002_add_chat_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add fields to documents table
    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.UUID(), nullable=True))
        batch_op.add_column(sa.Column("status", sa.String(length=50), server_default="uploaded", nullable=False))
        batch_op.add_column(sa.Column("error_message", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("file_path", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("original_filename", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("file_size", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("mime_type", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("metadata_json", sa.JSON().with_variant(JSONB(), "postgresql"), server_default=sa.text("'{}'"), nullable=False))
        batch_op.create_foreign_key("fk_documents_user_id_users", "users", ["user_id"], ["id"], ondelete="CASCADE")
        batch_op.create_index(batch_op.f("ix_documents_user_id"), ["user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_documents_status"), ["status"], unique=False)

    # 2. Add fields to document_chunks table
    with op.batch_alter_table("document_chunks") as batch_op:
        batch_op.add_column(sa.Column("chunk_index", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("token_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("document_chunks") as batch_op:
        batch_op.drop_column("token_count")
        batch_op.drop_column("chunk_index")

    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_index(batch_op.f("ix_documents_status"))
        batch_op.drop_index(batch_op.f("ix_documents_user_id"))
        batch_op.drop_constraint("fk_documents_user_id_users", type_="foreignkey")
        batch_op.drop_column("metadata_json")
        batch_op.drop_column("mime_type")
        batch_op.drop_column("file_size")
        batch_op.drop_column("original_filename")
        batch_op.drop_column("file_path")
        batch_op.drop_column("error_message")
        batch_op.drop_column("status")
        batch_op.drop_column("user_id")
