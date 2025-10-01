from typing import Any, AsyncGenerator, Optional
from asyncio import sleep
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine
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
engine: Optional[AsyncEngine] = None
AsyncSessionLocal: Optional[async_sessionmaker] = None


async def init_engine(db_url: str, max_retries: int = 10, retry_delay: float = 1.0) -> None:
    # we gotta modify the pre-existing SQLAlchemy engine & async session
    global engine, AsyncSessionLocal
    # just exit if the engine has already been initialized
    if engine:
        return

    engine = create_async_engine(
        db_url,
        pool_pre_ping=True
    )
    AsyncSessionLocal = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession)

    # try to acquire a connection to the database in order to verify that's ready to be used
    last_exc = None
    for _ in range(max_retries):
        try:
            async with engine.begin() as conn:
                # acts as a no-op that verifies the connection
                await conn.run_sync(lambda _: None)
            return
        except Exception as e:
            last_exc = e
            await sleep(retry_delay)

    # if we didn't return, then we failed to connect with the database
    raise RuntimeError(
        f"Unable to connect with the database after {max_retries} tries: {last_exc}")


async def close_engine() -> None:
    global engine   # we gotta modify the pre-existing SQLAlchemy engine
    if engine:
        await engine.dispose()
        engine = None


# dependency for FastAPI routes
async def get_session() -> AsyncGenerator[Any, Any]:
    # if the async session hasn't been initialized, then tell the user that init_engine wasn't
    # been called when the app started up
    if not AsyncSessionLocal:
        raise RuntimeError(
            "The SQLAlchemy engine hasn't been initialized. You must call `init_engine` on app startup.")
    async with AsyncSessionLocal() as session:
        yield session
