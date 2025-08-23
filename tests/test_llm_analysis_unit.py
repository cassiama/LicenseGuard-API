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


class FakeLLM:
    """
    Minimal LLM double compatible with:
        structured_llm = llm.with_structured_output(AnalyzeResult)
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
        # if no explicit return is supplied, return a plain dict so that it can still be validated as AnalyzeResult
        return self._return or {
            "project_name": "Test Project",
            "analysis_date": date.today().isoformat(),
            "files": [
                {"name": "requests", "version": "2.32.3",
                 "license": "Apache-2.0", "confidence_score": 0.8}
            ],
        }

@pytest.mark.asyncio
async def test_get_llm_analysis_success(monkeypatch):
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
    fake = FakeLLM(return_val=result)
    monkeypatch.setattr("srv.app.llm", fake)

    await get_llm_analysis(project_id, project_name, reqs, db)

    assert db.get_calls == 1
    assert db.upsert_calls == 1

    rec = db.records[project_id]
    assert rec.status == Status.COMPLETED
    assert rec.result == result
    # function should overwrite record.name with provided project_name
    assert rec.name == project_name


@pytest.mark.asyncio
async def test_get_llm_analysis_creates_record_if_missing(monkeypatch):
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
    fake = FakeLLM(return_val=result)
    monkeypatch.setattr("srv.app.llm", fake)

    await get_llm_analysis(project_id, project_name, reqs, db)

    # one upsert performed to persist the new record w/ result
    assert db.upsert_calls == 1

    rec = db.records[project_id]
    assert rec.id == project_id
    assert rec.name == project_name
    assert rec.status == Status.COMPLETED
    assert rec.result == result


@pytest.mark.asyncio
async def test_get_llm_analysis_marks_failed_on_llm_error(monkeypatch):
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

    fake = FakeLLM(should_raise=True)
    monkeypatch.setattr("srv.app.llm", fake)

    await get_llm_analysis(project_id, project_name, reqs, db)

    # first get() to load the record, one upsert() to set status as FAILED
    assert db.get_calls >= 1
    assert db.upsert_calls == 1

    rec = db.records[project_id]
    assert rec.status == Status.FAILED
    assert rec.result is None


@pytest.mark.asyncio
async def test_llm_messages_contract(monkeypatch):
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

    fake = FakeLLM()
    monkeypatch.setattr("srv.app.llm", fake)

    await get_llm_analysis(project_id, project_name, reqs, db)

    # exactly one LLM call holding two messages
    assert len(fake.calls) == 1
    messages = fake.calls[0]
    assert len(messages) == 2, "expected [SystemMessage, HumanMessage]"

    # for asserting the system message, we know that at least today's ISO date is injected into the template
    assert date.today().isoformat() in messages[0].content

    # for the asserting the human message, we know that it at least includes project name and the packages
    content = messages[1].content
    assert project_name in content
    for line in reqs:
        assert line in content
