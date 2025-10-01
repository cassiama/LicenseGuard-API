from typing import Any, AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from core.config import get_settings

# the database is expected to be async, so we will only allow asynchronous connections
ALLOWED_CONN_PREFIXES = [
    "postgresql+asyncpg://",
    "sqlite+aiosqlite://",
    "mysql+aiomysql://",
    "mssql+aioodbc://",
]

# import the DB_URL variable
settings = get_settings()
DB_URL = str(settings.db_url) if settings.db_url else ""
if not any([DB_URL.startswith(conn_prefix) for conn_prefix in ALLOWED_CONN_PREFIXES]):
    raise RuntimeError(
        "Please provide an async DB connection URL (e.g. postgresql+asyncpg://user:pw@host:5432/dbname) for DB_URL.")

# create the engine and local session
engine = create_async_engine(
    DB_URL,
    pool_pre_ping=True
)
AsyncSessionLocal = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession)

# dependency for FastAPI routes


async def get_session() -> AsyncGenerator[Any, Any]:
    async with AsyncSessionLocal() as session:
        yield session
