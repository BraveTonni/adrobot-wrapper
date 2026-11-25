"""add durable idempotency records

Revision ID: b402e51d9a0c
Revises: 89896ed5ae38
Create Date: 2026-11-25
"""

import sqlalchemy as sa

from alembic import op

revision = "b402e51d9a0c"
down_revision = "89896ed5ae38"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "idempotency_records",
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("response", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("idempotency_records")
