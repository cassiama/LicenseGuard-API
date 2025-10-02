"""init tables

Revision ID: bdc4d0bc52c4
Revises: 
Create Date: 2025-10-02 07:41:15.228487

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bdc4d0bc52c4'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user",
        sa.Column("id", sa.UUID),
        sa.Column("username", sa.VARCHAR(100)),
        sa.Column("email", sa.TEXT, nullable=True),
        sa.Column("full_name", sa.TEXT, nullable=True),
        sa.Column("hashed_password", sa.TEXT)
    )
    op.create_primary_key("pk_user", "user", ["id"])
    op.create_index("ix_user_username", "user", ["username"])
    op.create_table(
        "event",
        sa.Column("id", sa.UUID),
        sa.Column("user_id", sa.UUID),
        sa.Column("project_name", sa.TEXT),
        sa.Column("event", sa.VARCHAR(18)),
        sa.Column("timestamp", sa.TIMESTAMP),
        sa.Column("content", sa.TEXT, nullable=True)
    )
    op.create_foreign_key("fk_event_user_id_user", "event", "user", ["user_id"], ["id"])
    op.create_index("ix_event_project_name", "event", ["project_name"])

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("pk_user", "user", "primary")
    op.drop_index("ix_user_username", "user")
    op.drop_table("user")
    op.drop_constraint("fk_event_user_id_user", "event", "foreignkey")
    op.drop_index("ix_event_project_name", "event")
    op.drop_table("event")
