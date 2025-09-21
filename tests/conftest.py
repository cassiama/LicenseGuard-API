import io
import sys
import re
import pytest
import asyncio
from pathlib import Path
from datetime import date
from typing import Generator
from fastapi.testclient import TestClient

# makes sure that "src" is importable without setting PYTHONPATH manually
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# NOTE: these imports MUST come after sys.path tweak, otherwise you won't be able to run the test suite
from srv.app import app
from srv.security import get_current_user
from srv.schemas import EventRecord, EventType, AnalysisResult, DependencyReport, User
from db.db import get_db


HEX32 = re.compile(r"^[0-9a-f]{32}$")
# regex taken from this: https://base64.guru/standards/base64url
BASE64URL = re.compile(r"^[A-Za-z0-9_-]+$")


# using this context manager will ensure FastAPI lifespan/startup/shutdown all end up running
@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    # make sure every test request is logged in as a fake user
    def _fake_user_dep() -> User:
        return User(
            id="test-user-id",
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



# helper class for seeding the *mock* DB
# NOTE: once a real DB is implemented, this will change
class SeededDB:
    """Tiny async mock that satisfies the event-logging DBClient protocol."""

    def __init__(self):
        self.events: list[EventRecord] = []

    async def connect(self): ...
    async def disconnect(self): ...

    async def upsert_event(self, record: EventRecord) -> None:
        self.events.append(record)

    async def get_project_events(self, user_id: str, project_name: str) -> list[EventRecord]:
        return [
            event for event in self.events
            if event.user_id == user_id and event.project_name == project_name
        ]



# helper function that returns a DB client while also seeding the mock DB
@pytest.fixture
def client_with_seed(client: TestClient):
    test_db = SeededDB()

    # seed a sequence of events for a completed project
    user_id = "9c2a06a435814724a8994ec9b48ff4cd"
    project_name = "MyCoolCompleteProject"
    seed_events = [
        EventRecord(
            user_id=user_id,
            project_name=project_name,
            event=EventType.PROJECT_CREATED,
            content="requests==2.28.1",
        ),
        EventRecord(
            user_id=user_id,
            project_name=project_name,
            event=EventType.ANALYSIS_STARTED,
        ),
        EventRecord(
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
            )
        ),
    ]

    # seed the DB
    for event in seed_events:
        asyncio.run(test_db.upsert_event(event))

    # override the app dependency to use the seeded mock
    app.dependency_overrides[get_db] = lambda: test_db
    try:
        yield client    # re-use the existing TestClient, don't create another
    finally:
        app.dependency_overrides.clear()
