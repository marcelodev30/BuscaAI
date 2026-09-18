"""create files table

Revision ID: 012809921d9d
Revises: 0355d10f92a4
Create Date: 2026-09-18 13:51:54.896753

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '012809921d9d'
down_revision: Union[str, Sequence[str], None] = '0355d10f92a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


file_status = postgresql.ENUM(
    "pending", "processing", "ready", "failed", "empty", "deleting", name="file_status", create_type=False
)


def upgrade() -> None:
    """Upgrade schema."""
    file_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "files",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "notebook_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notebooks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # identidade
        sa.Column("original_name", sa.String(500), nullable=False),
        sa.Column("source_key", sa.Text(), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        # estado
        sa.Column("status", file_status, nullable=False, server_default="pending"),
        sa.Column("stage", sa.String(30), nullable=True),
        sa.Column("progress", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        # fila
        sa.Column("attempt", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column("run_after", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("locked_by", sa.Text(), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        # checkpoint do processamento em lote
        sa.Column("chunks_total", sa.Integer(), nullable=True),
        sa.Column("chunks_done", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("batch_size", sa.SmallInteger(), nullable=False, server_default=sa.text("64")),
        # resultado
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        # versões, para saber o que vale reprocessar
        sa.Column("parser_version", sa.String(50), nullable=True),
        sa.Column("chunking_version", sa.Integer(), nullable=True),
        sa.Column("embedding_model", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "stage IS NULL OR stage IN ('extracting', 'chunking', 'embedding', 'indexing')",
            name="ck_files_stage",
        ),
        sa.UniqueConstraint("notebook_id", "checksum_sha256", name="uq_files_notebook_checksum"),
    )
    op.create_index("ix_files_user_id", "files", ["user_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("files")
    file_status.drop(op.get_bind(), checkfirst=True)
