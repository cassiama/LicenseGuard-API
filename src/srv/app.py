from typing import Annotated
from datetime import datetime, date
from uuid import uuid4
from fastapi import FastAPI, UploadFile, File, Depends, BackgroundTasks, status
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from core.config import Settings
from db.db import DBClient, get_db, lifespan
from .schemas import AnalyzeResponse, AnalyzeResult, ProjectRecord, Status
from .routers import llm as llm_router, status as status_router
from .validators import validate_requirements_file

app = FastAPI(lifespan=lifespan)
# all routes from this router are deprecated as of v0.2.0
app.include_router(llm_router.router)
app.include_router(status_router.router)

# LLM / OpenAI definitions
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.0,
    api_key=Settings().openai_api_key,
)

SYSTEM_PROMPT = (
    "You are a careful license analysis assistant. "
    "Given a Python requirements list, infer each package's SPDX license and a confidence score in [0,1]. "
    "If unsure, choose the most likely SPDX identifier and lower confidence accordingly. "
    "Only use SPDX identifiers for the 'license' field (e.g., MIT, Apache-2.0, BSD-3-Clause, GPL-3.0-only). "
    "Today's date is {today}. Return ONLY structured data that matches the schema."
)


# this route is deprecated as of v0.2.0 (might be reenabled later on, we'll see!)
@app.get("/", deprecated=True)
async def root():
    return {"message": "Hello World!"}


# helper function that calls a OpenAI LLM to analyze dependencies and returns a structured output
async def get_llm_analysis(project_id: str, reqs: list[str], db: DBClient):
    """
    Runs in a FastAPI BackgroundTask. Calls the LLM via LangChain with structured output
    and persists the result into the DB record. On error, marks FAILED.
    """
    try:
        # bind the Pydantic output schema directly to the LLM
        structured_llm = llm.with_structured_output(AnalyzeResult)

        messages = [
            SystemMessage(content=SYSTEM_PROMPT.format(today=date.today().isoformat())),
            # TODO: tell the LLM to use SPDX licensing format for the licenses.
            HumanMessage(content=(
                "Here are the packages from requirements.txt (one per line):\n\n"
                f"{"\n".join(reqs)}\n\n"
                "Also include a project_name (you may infer 'untitled' if none provided) "
                "and set analysis_date to today's date. Use the following guide to "
                "determine the confidence score of the licenses: "
                "1.0: Perfect classifier like \"License :: OSI Approved :: MIT License\""
                "0.9: Multiple consistent indicators"
                "0.7: Clear license field like \"MIT\""
                "0.5: Ambiguous like \"License :: OSI Approved\" (no specific license)"
                "0.3: Vague like \"Apache\" (could be 1.0 or 2.0)"
                "0.1: Very unclear like \"BSD\" (which variant?)"
            ))
        ]

        result = structured_llm.invoke(messages)

        # persist the result & status to the DB
        record = await db.get_project(project_id)
        if record is None:
            # if record didn't persist to the DB yet (rare and shouldn't happen, but possible), create a small one to store result
            record = ProjectRecord(
                id=project_id,
                name="untitled",
                status=Status.IN_PROGRESS,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                result=None,
            )

        record.result = result
        record.status = Status.COMPLETED
        record.updated_at = datetime.now()
        await db.upsert_project(record)
    except Exception as e:  # when the LLM fails...
        try:    # try to update the record with a FAILED status

            record: ProjectRecord | None = await db.get_project(project_id)
            if record:
                record.status = Status.FAILED
                record.updated_at = datetime.now()
                await db.upsert_project(record)
        finally:    # regardless of even *that* failing, make sure to log that the LLM failed.
            print(f"[{datetime.now()}] get_llm_analysis failed for {project_id}: {e}")

@app.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def analyze_dependencies(
    file: Annotated[UploadFile, File(
        description="A requirements.txt file (text/plain).")],
    bg_tasks: BackgroundTasks,
    # TODO: consider a project_name so that the user can actually name this project
    db: DBClient = Depends(get_db),
) -> AnalyzeResponse:
    """
    Accepts a requirements.txt file upload, analyzes each license associated with the dependencies in the 'requirements.txt' file, and returns a new project.
    NOTE: Result is null until the analysis step is implemented.

    Keyword arguments:
    file -- an non-empty 'requirements.txt'
    """
    _reqs = await validate_requirements_file(file)  # validate & parse the requirements

    project_id = uuid4().hex
    record = ProjectRecord(
        id=project_id,
        # name=project_name or "untitled",
        name="untitled",
        status=Status.IN_PROGRESS,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        result=None,
    )
    await db.upsert_project(record)

    bg_tasks.add_task(get_llm_analysis, project_id=project_id, reqs=_reqs, db=db) # call the LLM and let it handle the analysis of the requirements

    return AnalyzeResponse(
        project_id=project_id,
        status=Status.IN_PROGRESS,
        result=None
    )
