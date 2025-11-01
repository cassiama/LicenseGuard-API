"""seeded DB with a MCP service user

Revision ID: be547e80351d
Revises: bdc4d0bc52c4
Create Date: 2025-10-26 21:28:16.212532

"""
import os
from typing import Sequence, Union
from secrets import token_hex
from uuid import uuid4
from passlib.context import CryptContext

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be547e80351d'
down_revision: Union[str, Sequence[str], None] = 'bdc4d0bc52c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# setup password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# import the MCP client ID and secret from the environment variables
MCP_CLIENT_ID = os.getenv("MCP_CLIENT_ID", "mcp-server")
MCP_CLIENT_SECRET = os.getenv("MCP_CLIENT_SECRET", token_hex(16))


def upgrade() -> None:
    """Upgrade schema."""
    user_table = sa.sql.table(
        "user",
        sa.Column("id", sa.VARCHAR(36), primary_key=True, nullable=False),
        sa.Column("username", sa.VARCHAR(100), unique=True, index=True, nullable=False),
        sa.Column("email", sa.TEXT, nullable=True),
        sa.Column("full_name", sa.TEXT, nullable=True),
        sa.Column("hashed_password", sa.TEXT, nullable=False)
    )
    op.bulk_insert(
        user_table,
        [
            {
                "id": str(uuid4()),
                "username": MCP_CLIENT_ID,
                "hashed_password": pwd_context.hash(MCP_CLIENT_SECRET),
            }

        ]
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
