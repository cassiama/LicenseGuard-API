import pytest
from datetime import date
from srv.app import get_llm_analysis
from srv.schemas import AnalysisResult, DependencyReport


@pytest.mark.asyncio
async def test_get_llm_analysis_success(fake_llm):
    """Tests that `get_llm_analysis()` returns a successful AnalysisResult."""
    project_name = "binder-examples"
    reqs = ["requests==2.32.3", "fastapi>=0.95.0"]

    expected_result = AnalysisResult(
        project_name=project_name,
        analysis_date=date.today(),
        files=[
            DependencyReport(name="requests", version="2.32.3",
                             license="Apache-2.0", confidence_score=0.8),
            DependencyReport(name="fastapi", version="0.95.0",
                             license="MIT", confidence_score=0.9),
        ],
    )
    fake_llm._return = expected_result

    result = await get_llm_analysis(project_name, reqs)
    assert result == expected_result


@pytest.mark.asyncio
async def test_get_llm_analysis_handles_exceptions(fake_llm):
    """Tests that `get_llm_analysis()` handles exceptions properly."""
    project_name = "abandoned-project"
    reqs = ["requests==2.32.3"]
    fake_llm._raise = True

    result = await get_llm_analysis(project_name, reqs)
    assert result is None


@pytest.mark.asyncio
async def test_llm_messages_contract(fake_llm):
    """Tests that `get_llm_analysis()` sends a SystemMessage and a HumanMessage with expected content."""
    project_name = "Format Test"
    reqs = ["requests==2.32.3", "fastapi>=0.95.0"]

    await get_llm_analysis(project_name, reqs)

    assert len(fake_llm.calls) == 1
    messages = fake_llm.calls[0]
    assert len(messages) == 2, "expected [SystemMessage, HumanMessage]"

    assert date.today().isoformat() in messages[0].content

    content = messages[1].content
    assert project_name in content
    for line in reqs:
        assert line in content
