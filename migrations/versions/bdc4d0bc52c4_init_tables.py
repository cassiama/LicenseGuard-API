"""init tables

Revision ID: bdc4d0bc52c4
Revises: 
Create Date: 2025-10-02 07:41:15.228487

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mssql


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
        sa.Column("project_name", sa.VARCHAR(100), index=True, nullable=False),
        sa.Column("event", sa.VARCHAR(18), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True).with_variant(mssql.DATETIMEOFFSET(precision=6), "mssql"), nullable=False),
        sa.Column("content", sa.TEXT, nullable=True)
    )

    conn = op.get_bind()
    dialect = conn.dialect.name

    fk_name = "fk_event_user_id_user"

    exists = False
    if dialect == "mssql":
        # SQL Server: sys.foreign_keys
        res = conn.execute(sa.text(
            "SELECT COUNT(*) FROM sys.foreign_keys WHERE name = :name"
        ), {"name": fk_name})
        exists = res.scalar() is not None
    elif dialect == "postgresql":
        res = conn.execute(sa.text(
            "SELECT COUNT(*) FROM information_schema.table_constraints "
            "WHERE constraint_name = :name AND constraint_type='FOREIGN KEY'"
        ), {"name": fk_name})
        exists = res.scalar() is not None
    elif dialect == "mysql":
        res = conn.execute(sa.text(
            "SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS "
            "WHERE CONSTRAINT_NAME = :name AND CONSTRAINT_SCHEMA = DATABASE()"
        ), {"name": fk_name})
        exists = res.scalar() is not None
    elif dialect == "sqlite":
        # SQLite: check pragma
        res = conn.execute(sa.text("PRAGMA foreign_key_list('event')"))
        exists = any(row[2] == 'user' and row[3] == 'user_id' for row in res.fetchall())

    if not exists:
        with op.batch_alter_table("event", schema=None) as batch_op:
            batch_op.create_foreign_key(
                fk_name, "user", ["user_id"], ["id"], ondelete="CASCADE"
            )

def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("event", schema=None) as batch_op:
        batch_op.drop_constraint("fk_event_user_id_user", type_="foreignkey")
    op.drop_index("ix_user_username", "user")
    op.drop_table("user")
    op.drop_index("ix_event_project_name", "event")
    op.drop_table("event")
