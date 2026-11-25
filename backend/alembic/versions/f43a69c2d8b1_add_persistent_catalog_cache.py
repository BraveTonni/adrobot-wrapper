"""add persistent catalog cache

Revision ID: f43a69c2d8b1
Revises: d4a77fcd8e11
Create Date: 2026-11-25
"""

import sqlalchemy as sa

from alembic import op

revision = "f43a69c2d8b1"
down_revision = "d4a77fcd8e11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalog_cache",
        sa.Column("key", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("catalog_cache")
