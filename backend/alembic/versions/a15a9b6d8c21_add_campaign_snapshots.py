"""add local campaign snapshots

Revision ID: a15a9b6d8c21
Revises: f43a69c2d8b1
Create Date: 2026-11-25
"""

import sqlalchemy as sa

from alembic import op

revision = "a15a9b6d8c21"
down_revision = "f43a69c2d8b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campaign_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("alias", sa.String(length=255), nullable=True),
        sa.Column("type", sa.String(length=40), nullable=True),
        sa.Column("state", sa.String(length=40), nullable=True),
        sa.Column("domain_id", sa.Integer(), nullable=True),
        sa.Column("group_id", sa.Integer(), nullable=True),
        sa.Column("traffic_source_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "stream_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("type", sa.String(length=40), nullable=True),
        sa.Column("schema", sa.String(length=40), nullable=True),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("state", sa.String(length=40), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["campaign_snapshots.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "stream_offer_snapshots",
        sa.Column("stream_id", sa.Integer(), nullable=False),
        sa.Column("offer_id", sa.Integer(), nullable=False),
        sa.Column("share", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=True),
        sa.Column("is_pinned", sa.Boolean(), nullable=False),
        sa.Column("published_share", sa.Integer(), nullable=False),
        sa.Column("published_state", sa.String(length=40), nullable=True),
        sa.Column("draft_share", sa.Integer(), nullable=False),
        sa.Column("draft_state", sa.String(length=40), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("metadata_payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["stream_id"], ["stream_snapshots.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("stream_id", "offer_id"),
    )


def downgrade() -> None:
    op.drop_table("stream_offer_snapshots")
    op.drop_table("stream_snapshots")
    op.drop_table("campaign_snapshots")
