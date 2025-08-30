import pytest
from datetime import datetime, date
from srv.app import get_llm_analysis
from srv.schemas import AnalyzeResult, DependencyReport, ProjectRecord, Status

class DBSpy:
    """
    Minimal async DB double that behaves like DBClient and lets us assert on effects without AsyncMock. Stores records in-memory and tracks simple counters.
    """
    def __init__(self):
        self.records: dict[str, ProjectRecord] = {}
        self.upsert_calls = 0
        self.get_calls = 0

    async def connect(self): ...
    async def disconnect(self): ...

    async def upsert_project(self, record: ProjectRecord) -> None:
        self.upsert_calls += 1
        self.records[record.id] = record

    async def get_project(self, project_id: str):
        self.get_calls += 1
        return self.records.get(project_id)

    async def set_status(self, project_id: str, status: Status) -> None:
        if project_id in self.records:
            rec = self.records[project_id]
            rec.status = status
            rec.updated_at = datetime.now()

    async def seed(self, record: ProjectRecord):
        self.records[record.id] = record


@pytest.mark.asyncio
async def test_get_llm_analysis_success(fake_llm):
    """Persists result and marks COMPLETED when the LLM succeeds."""
    project_id = "b40dcbeabd1d42a3bb4b48b8a2186639"
    project_name = "binder-examples"
    reqs = ["requests==2.32.3", "fastapi>=0.95.0"]

    db = DBSpy()
    await db.seed(ProjectRecord(
        id=project_id,
        name="temp-name",
        status=Status.IN_PROGRESS,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        result=None,
    ))

    result = AnalyzeResult(
        project_name=project_name,
        analysis_date=date.today(),
        files=[
            DependencyReport(name="requests", version="2.32.3",
                             license="Apache-2.0", confidence_score=0.8),
            DependencyReport(name="fastapi", version="0.95.0",
                             license="MIT", confidence_score=0.9),
        ],
    )
    fake_llm._return = result

    await get_llm_analysis(project_id, project_name, reqs, db)

    assert db.get_calls == 1
    assert db.upsert_calls == 1

    rec = db.records[project_id]
    assert rec.status == Status.COMPLETED
    assert rec.result == result
    assert rec.name == project_name


@pytest.mark.asyncio
async def test_get_llm_analysis_creates_record_if_missing(fake_llm):
    """If DB has no record, function creates one and completes with result."""
    project_id = "5bf10c5bf28546a587365dc7a5929511"
    project_name = "fastapi"
    reqs = ["requests==2.32.3"]

    db = DBSpy()  # intentionally empty

    result = AnalyzeResult(
        project_name=project_name,
        analysis_date=date.today(),
        files=[DependencyReport(name="requests", version="2.32.3",
                                license="Apache-2.0", confidence_score=0.8)],
    )
    fake_llm._return = result

    await get_llm_analysis(project_id, project_name, reqs, db)

    assert db.upsert_calls == 1

    rec = db.records[project_id]
    assert rec.id == project_id
    assert rec.name == project_name
    assert rec.status == Status.COMPLETED
    assert rec.result == result


@pytest.mark.asyncio
async def test_get_llm_analysis_marks_failed_on_llm_error(fake_llm):
    """On LLM exception, mark FAILED and keep result None."""
    project_id = "713f73a19836401bb73cdf3517f779a7"
    project_name = "abandoned-project"
    reqs = ["requests==2.32.3"]

    db = DBSpy()
    await db.seed(ProjectRecord(
        id=project_id,
        name=project_name,
        status=Status.IN_PROGRESS,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        result=None,
    ))

    fake_llm._raise = True

    await get_llm_analysis(project_id, project_name, reqs, db)

    assert db.get_calls >= 1
    assert db.upsert_calls == 1

    rec = db.records[project_id]
    assert rec.status == Status.FAILED
    assert rec.result is None


@pytest.mark.asyncio
async def test_llm_messages_contract(fake_llm):
    """
    The function should send a SystemMessage (with today's date injected) and a HumanMessage containing the project_name and the requirement lines.
    """
    project_id = "format123"
    project_name = "Format Test"
    reqs = ["requests==2.32.3", "fastapi>=0.95.0"]

    db = DBSpy()
    await db.seed(ProjectRecord(
        id=project_id,
        name="seeded",
        status=Status.IN_PROGRESS,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        result=None,
    ))

    await get_llm_analysis(project_id, project_name, reqs, db)

    assert len(fake_llm.calls) == 1
    messages = fake_llm.calls[0]
    assert len(messages) == 2, "expected [SystemMessage, HumanMessage]"

    assert date.today().isoformat() in messages[0].content

    content = messages[1].content
    assert project_name in content
    for line in reqs:
        assert line in content