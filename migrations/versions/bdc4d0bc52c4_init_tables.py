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
        sa.Column("id", sa.VARCHAR(36), primary_key=True, nullable=False),
        sa.Column("username", sa.VARCHAR(100), unique=True, index=True, nullable=False),
        sa.Column("email", sa.TEXT, nullable=True),
        sa.Column("full_name", sa.TEXT, nullable=True),
        sa.Column("hashed_password", sa.TEXT, nullable=False)
    )

    op.create_table(
        "event",
        sa.Column("id", sa.VARCHAR(36), primary_key=True),
        sa.Column("user_id", sa.VARCHAR(36), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_name", sa.TEXT, index=True, nullable=False),
        sa.Column("event", sa.VARCHAR(18), nullable=False),
        sa.Column("timestamp", sa.TIMESTAMP, nullable=False),
        sa.Column("content", sa.TEXT, nullable=True)
    )
    with op.batch_alter_table("event", schema=None) as batch_op:
        batch_op.create_foreign_key("fk_event_user_id_user", "user", ["user_id"], ["id"])

def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("event", schema=None) as batch_op:
        batch_op.drop_constraint("fk_event_user_id_user", type_="foreignkey")
    op.drop_index("ix_user_username", "user")
    op.drop_table("user")
    op.drop_index("ix_event_project_name", "event")
    op.drop_table("event")
