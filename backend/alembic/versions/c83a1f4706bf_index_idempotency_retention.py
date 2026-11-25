"""index idempotency retention queries

Revision ID: c83a1f4706bf
Revises: b402e51d9a0c
Create Date: 2026-11-25
"""

from alembic import op

revision = "c83a1f4706bf"
down_revision = "b402e51d9a0c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_idempotency_records_status_created",
        "idempotency_records",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_idempotency_records_status_created",
        table_name="idempotency_records",
    )
