import os
import io
import sys
import re
import pytest
import asyncio
from uuid import uuid4
from pathlib import Path
from datetime import date
from typing import AsyncGenerator, Generator, Any
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine
from sqlmodel import SQLModel


# for tests that interact with the DB, create a SQLite file per-test session
TEST_DB_FILE = "./test_sqlite.db"
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE}"

# will create a safe test default for the DB_URL variable
# NOTE: this MUST come before we import the app, otherwise the test suite will fail to run
# NOTE: the test suite will fail to run without this default value
os.environ.setdefault("DB_URL", TEST_DB_URL)


# makes sure that "src" is importable without setting PYTHONPATH manually
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# NOTE: these imports MUST come after sys.path tweak, otherwise you won't be able to run the test suite
from srv.app import app
from srv.security import get_current_user
from srv.schemas import Event, EventType, AnalysisResult, DependencyReport, User, UserPublic
from db.session import get_db

# regex taken from this source: https://regex101.com/r/wL7uN1/1
HEX32 = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12}|[0-9a-f]{12}4[0-9a-f]{19}")
# regex taken from this source: https://base64.guru/standards/base64url
BASE64URL = re.compile(r"^[A-Za-z0-9_-]+$")


# using this context manager will ensure FastAPI lifespan/startup/shutdown all end up running
@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    # make sure every test request is logged in as a fake user
    def _fake_user_dep() -> UserPublic:
        return UserPublic(
            id=uuid4(),
            username="testuser",
            full_name="Test User",
            email="testuser@example.org",
        )

    app.dependency_overrides[get_current_user] = _fake_user_dep

    with TestClient(app) as c:
        yield c

    # doing this prevents other overrides from having conflicts
    app.dependency_overrides.pop(get_current_user, None)


# helper for POSTing a multipart file
@pytest.fixture
def post_file(client: TestClient):
    def _post(
        filename: str,
        data: bytes,
        content_type: str = "text/plain",
        form: dict | None = None
    ):
        files = {"file": (filename, io.BytesIO(data), content_type)}
        return client.post("/analyze", files=files, data=form or {"project_name": "untitled"})
    return _post


class FakeLLM:
    """
    Minimal LLM double compatible with:
        structured_llm = llm.with_structured_output(AnalysisResult)
        await structured_llm.ainvoke(messages)
    Captures messages for assertions.
    """

    def __init__(self, return_val=None, should_raise: bool = False):
        self._return = return_val
        self._raise = should_raise
        self.calls: list[list] = []  # list of message lists

    def with_structured_output(self, _):
        return self

    async def ainvoke(self, messages):
        self.calls.append(messages)
        if self._raise:
            raise Exception("LLM invocation failed")
        # if no explicit return is supplied, return a plain dict so that it can still be validated as AnalysisResult
        return self._return or {
            "project_name": "Test Project",
            "analysis_date": date.today().isoformat(),
            "files": [
                {"name": "requests", "version": "2.32.3",
                 "license": "Apache-2.0", "confidence_score": 0.8}
            ],
        }


@pytest.fixture
def fake_llm(monkeypatch):
    llm = FakeLLM()
    monkeypatch.setattr("srv.app.llm", llm)
    return llm


# create an event loop for the test session
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine() -> AsyncGenerator[Any, Any]:
    # ensure SQLite file from previous runs removed
    try:
        os.remove(TEST_DB_FILE)
    except OSError:
        pass

    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()
    try:
        os.remove(TEST_DB_FILE)
    except OSError:
        pass


@pytest.fixture
async def session_override(test_engine):
    SessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)
    async def _get_test_session():
        async with SessionLocal() as session:
            yield session
    
    app.dependency_overrides[get_db] = _get_test_session
    yield


# helper function that returns a DB client while also seeding the mock DB
@pytest.fixture
def client_with_seed(client: TestClient):
    # seed a sequence of events for a completed project
    async def _seed():
        get_test_session = app.dependency_overrides[get_db]
        async with get_test_session() as session:
            # add the test user
            user_id = uuid4()
            username = "johndoe"
            full_name = "John Doe"
            email = "johndoe@example.com"
            password = "secret"
            user = User(
                id=user_id,
                username=username,
                full_name=full_name,
                email=email,
                hashed_password=password
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            # add the events
            project_name = "MyCoolCompleteProject"
            seed_events = [
                Event(
                    id=uuid4(),
                    user_id=user_id,
                    project_name=project_name,
                    event=EventType.PROJECT_CREATED,
                    content="requests==2.28.1",
                ),
                Event(
                    id=uuid4(),
                    user_id=user_id,
                    project_name=project_name,
                    event=EventType.ANALYSIS_STARTED,
                ),
                Event(
                    id=uuid4(),
                    user_id=user_id,
                    project_name=project_name,
                    event=EventType.ANALYSIS_COMPLETED,
                    content=AnalysisResult(
                        project_name=project_name,
                        analysis_date=date.today(),
                        files=[
                            DependencyReport(
                                name="requests",
                                version="2.28.1",
                                license="Apache-2.0",
                                confidence_score=1.0
                            )
                        ],
                    ).model_dump_json()
                ),
            ]

            session.add_all(seed_events)
            await session.commit()

    # seed the DB
    asyncio.get_event_loop().run_until_complete(_seed())

    try:
        yield client    # re-use the existing TestClient, don't create another
    finally:
        app.dependency_overrides.clear()
