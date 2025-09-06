import io
import sys
import re
import pytest
import asyncio
from pathlib import Path
from datetime import datetime, date
from typing import Generator
from fastapi.testclient import TestClient

# makes sure that "src" is importable without setting PYTHONPATH manually
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from srv.schemas import ProjectRecord, Status, AnalysisResult, DependencyReport
from db.db import get_db
from srv.app import app

# NOTE: these imports MUST come after sys.path tweak, otherwise you won't be able to run the test suite

HEX32 = re.compile(r"^[0-9a-f]{32}$")

# using this context manager will ensure FastAPI lifespan/startup/shutdown all end up running


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c

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
        return client.post("/analyze", files=files, data=form or {})
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
    """Tiny async mock that satisfies the DBClient protocol for tests."""

    def __init__(self):
        self.records: dict[str, ProjectRecord] = {}

    async def connect(self): ...
    async def disconnect(self): ...

    async def upsert_project(self, record: ProjectRecord) -> None:
        self.records[record.id] = record

    async def get_project(self, project_id: str):
        return self.records.get(project_id)

    async def set_status(self, project_id: str, status: Status) -> None:
        if project_id in self.records:
            rec = self.records[project_id]
            rec.status = status
            rec.updated_at = datetime.now()

# helper function that returns a DB client while also seeding the mock DB


@pytest.fixture
def client_with_seed(client: TestClient):
    test_db = SeededDB()

    # seed two projects: one IN_PROGRESS with no result, one COMPLETED with result
    in_progress = ProjectRecord(
        id="9c2a06a435814724a8994ec9b48ff4cd",
        name="MyLameIncompleteProject",
        status=Status.IN_PROGRESS,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        result=None,
    )

    completed = ProjectRecord(
        id="776eaf11601c429783d23248b361d2b8",
        name="MyCoolCompleteProject",
        status=Status.COMPLETED,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        result=AnalysisResult(
            project_name="MyCoolCompleteProject",
            analysis_date=date.today(),
            files=[
                DependencyReport(name="contourpy", version="1.3.1",
                                 license="BSD-3-Clause", confidence_score=0.80),
                DependencyReport(name="contourpy", version="1.3.1",
                                 license="BSD-3-Clause", confidence_score=0.80)
            ],
        ),
    )

    # seed the DB
    asyncio.run(test_db.upsert_project(in_progress))
    asyncio.run(test_db.upsert_project(completed))

    # override the app dependency to use the seeded mock
    app.dependency_overrides[get_db] = lambda: test_db
    try:
        yield client    # re-use the existing TestClient, don't create another
    finally:
        app.dependency_overrides.clear()
