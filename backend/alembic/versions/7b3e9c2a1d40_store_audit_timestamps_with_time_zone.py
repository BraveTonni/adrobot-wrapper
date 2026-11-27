"""store audit timestamps with time zone

Revision ID: 7b3e9c2a1d40
Revises: a15a9b6d8c21
Create Date: 2026-11-28

Приложение пишет время в UTC с таймзоной, а PostgreSQL принимает такое
значение только в колонку WITH TIME ZONE: без этой миграции на PostgreSQL
падает каждая запись аудита, а значит и каждая операция с кампанией.
Существующие значения записаны как UTC без таймзоны.
"""

import sqlalchemy as sa

from alembic import op

revision = "7b3e9c2a1d40"
down_revision = "a15a9b6d8c21"
branch_labels = None
depends_on = None

_UTC = "created_at AT TIME ZONE 'UTC'"


def upgrade() -> None:
    with op.batch_alter_table("audit_log") as batch:
        batch.alter_column(
            "created_at",
            existing_type=sa.DateTime(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=False,
            existing_server_default=sa.text("(CURRENT_TIMESTAMP)"),
            postgresql_using=_UTC,
        )


def downgrade() -> None:
    with op.batch_alter_table("audit_log") as batch:
        batch.alter_column(
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(),
            existing_nullable=False,
            existing_server_default=sa.text("(CURRENT_TIMESTAMP)"),
            postgresql_using=_UTC,
        )
