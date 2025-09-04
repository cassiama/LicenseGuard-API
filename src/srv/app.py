from typing import Annotated
from datetime import datetime, date
from uuid import uuid4
from fastapi import FastAPI, Form, UploadFile, File, Depends, status
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from core.config import Settings
from db.db import DBClient, get_db, lifespan
from .schemas import AnalyzeResponse, AnalyzeResult, ProjectRecord, Status, User
from .routers import llm as llm_router, status as status_router, users as users_router
from .validators import validate_requirements_file
from .security import get_current_user

app = FastAPI(lifespan=lifespan)
app.include_router(users_router.router)
# all routes from this router are deprecated as of v0.2.0
app.include_router(llm_router.router)
# all routes from this router are deprecated as of v0.3.0
app.include_router(status_router.router)


app = FastAPI()


# importing secrets from the .env file
settings = Settings()
if not settings.openai_api_key:
    raise RuntimeError("OPENAI_API_KEY is required to call the LLM.")

# LLM / OpenAI definitions
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.0,
    api_key=settings.openai_api_key,
)

SYSTEM_PROMPT = (
    "You are a license analysis assistant.\n"
    "Rules for the single `license` field:\n"
    "• If and only if confidence_score == 1.0, set `license` to the full Trove classifier string "
    "(e.g., 'License :: OSI Approved :: MIT License').\n"
    "• Otherwise, set `license` to a valid SPDX identifier (e.g., MIT, Apache-2.0, BSD-3-Clause, GPL-3.0-only).\n"
    "• confidence_score must be in the range of [0,1].\n"
    "• Output MUST validate against the schema.\n"
    "Today's date is {today}."
)

FEW_SHOT = (
    "EXAMPLES (follow closely):\n"
    "Input pkgs:\n"
    "flask_socketio==5.5.1\n"
    "# Classifiers indicate MIT specifically\n\n"
    "Output item (since perfect Trove exists):\n"
    "{\"name\":\"flask_socketio\",\"version\":\"5.5.1\",\"license\":\"License :: OSI Approved :: MIT License\",\"confidence_score\":1.0}\n"
    "Input pkgs:\n"
    "urllib3==2.2.2\n"
    "# SPDX clearly says MIT; Trove may be generic or missing\n\n"
    "Output item (no perfect Trove known):\n"
    "{\"name\":\"urllib3\",\"version\":\"2.2.2\",\"license\":\"MIT\",\"confidence_score\":0.7}\n"
)


# this route is deprecated as of v0.2.0 (might be reenabled later on, we'll see!)
@app.get("/", deprecated=True)
async def root():
    return {"message": "Hello World!"}


# helper function that calls a OpenAI LLM to analyze dependencies and returns a structured output
async def get_llm_analysis(
    project_id: str,
    project_name: str,
    reqs: list[str],
    db: DBClient
):
    """
    Runs in a FastAPI BackgroundTask. Calls the LLM via LangChain with structured output
    and persists the result into the DB record. On error, marks FAILED.
    """
    try:
        # bind the Pydantic output schema directly to the LLM
        structured_llm = llm.with_structured_output(AnalyzeResult)

        messages = [
            SystemMessage(content=SYSTEM_PROMPT.format(
                today=date.today().isoformat())),
            HumanMessage(content=(
                f"{FEW_SHOT}\n\n"
                "Here are the packages from requirements.txt (one per line). "
                "Remember the single-field rule for `license`:\n\n"
                f"{"\n".join(reqs)}\n\n"
                f"Use this exact project name: {project_name} "
                "(you may infer 'untitled' if none provided) "
                "and set analysis_date to today's date. "
            ))
        ]

        result: AnalyzeResult = AnalyzeResult.model_validate(await structured_llm.ainvoke(messages))

        # persist the result & status to the DB
        record: ProjectRecord | None = await db.get_project(project_id)
        if record is None:
            # if record didn't persist to the DB yet (rare and shouldn't happen, but possible), create a small one to store result
            record = ProjectRecord(
                id=project_id,
                name=project_name,
                status=Status.IN_PROGRESS,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                result=None,
            )

        record.name = project_name
        record.result = result
        record.status = Status.COMPLETED
        record.updated_at = datetime.now()
        await db.upsert_project(record)
        return result

    except Exception as e:  # when the LLM fails...
        try:    # try to update the record with a FAILED status

            record: ProjectRecord | None = await db.get_project(project_id)
            if record:
                record.status = Status.FAILED
                record.updated_at = datetime.now()
                await db.upsert_project(record)
        # regardless of even *that* failing, make sure to log that the LLM failed.
        finally:
            print(
                f"[{datetime.now()}] get_llm_analysis failed for {project_id}: {e}")
            return None


@app.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
)
async def analyze_dependencies(
    file: Annotated[UploadFile, File(
        description="A requirements.txt file (text/plain).")],
    _user: Annotated[User, Depends(get_current_user)],
    db: DBClient = Depends(get_db),
    project_name: Annotated[str, Form(
        description="The name of the project")] = "untitled",
) -> AnalyzeResponse:
    """
    Accepts a requirements.txt file upload and a project name, analyzes each license associated with the dependencies in the 'requirements.txt' file, and returns the analysis.

    Throws a 400 if the uploaded file is empty.

    Throws a 401 if the user is unauthorized.

    Throws a 415 if the uploaded file has an unsupported MIME type.

    Throws a 422 if:
     - the uploaded file does not have a .txt extension.
     - there is a Unicode decode error while processing the file.
     - the requirements.txt file is invalid and cannot be parsed.
     - no valid requirements are found in the file.

    Keyword arguments:

    file -- an non-empty 'requirements.txt'

    project_name -- the name of your project (default: "untitled")
    """
    _reqs = await validate_requirements_file(file)  # validate & parse the requirements

    project_id = uuid4().hex
    record = ProjectRecord(
        id=project_id,
        name=project_name,
        status=Status.IN_PROGRESS,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        result=None,
    )
    await db.upsert_project(record)

    # retrieve the analysis from the LLM
    llm_result = await get_llm_analysis(project_id, project_name, _reqs, db)

    if llm_result is None:
        return AnalyzeResponse(
            project_id=project_id,
            status=Status.FAILED,
            result=llm_result
        )

    return AnalyzeResponse(
        project_id=project_id,
        status=Status.COMPLETED,
        result=llm_result
    )
