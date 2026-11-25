"""expand operations into audit log

Revision ID: d4a77fcd8e11
Revises: c83a1f4706bf
Create Date: 2026-11-25
"""

import sqlalchemy as sa

from alembic import op

revision = "d4a77fcd8e11"
down_revision = "c83a1f4706bf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("operations", "audit_log")
    op.add_column(
        "audit_log",
        sa.Column(
            "actor",
            sa.String(length=150),
            server_default="unknown",
            nullable=False,
        ),
    )
    op.add_column(
        "audit_log",
        sa.Column(
            "entity_type",
            sa.String(length=40),
            server_default="operation",
            nullable=False,
        ),
    )
    op.add_column(
        "audit_log", sa.Column("entity_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "audit_log", sa.Column("before_payload", sa.JSON(), nullable=True)
    )
    op.add_column(
        "audit_log", sa.Column("after_payload", sa.JSON(), nullable=True)
    )
    op.add_column("audit_log", sa.Column("error", sa.Text(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE audit_log SET entity_type = CASE "
            "WHEN action LIKE 'campaign.%' THEN 'campaign' "
            "WHEN action LIKE 'stream.%' THEN 'stream' "
            "ELSE 'operation' END, "
            "entity_id = COALESCE(stream_id, campaign_id)"
        )
    )


def downgrade() -> None:
    op.drop_column("audit_log", "error")
    op.drop_column("audit_log", "after_payload")
    op.drop_column("audit_log", "before_payload")
    op.drop_column("audit_log", "entity_id")
    op.drop_column("audit_log", "entity_type")
    op.drop_column("audit_log", "actor")
    op.rename_table("audit_log", "operations")
