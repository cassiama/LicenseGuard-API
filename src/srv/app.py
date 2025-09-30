from typing import Annotated, Optional
from datetime import datetime, date, timezone
from email.utils import format_datetime
from uuid import uuid4
from fastapi import FastAPI, Form, HTTPException, UploadFile, File, Depends, status
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from sqlmodel.ext.asyncio.session import AsyncSession
from core.config import get_settings
from crud.events import add_event
from db.session import get_db
from .schemas import AnalyzeResponse, AnalysisResult, Event, EventType, Status, UserPublic
from .routers import llm as llm_router, status as status_router, users as users_router
from .validators import parse_requirements_file, validate_requirements_file
from .security import get_current_user

# corresponds to commit 11b42e4
DEPRECATION_DATE = datetime(2025, 8, 21, 22, 23, 6, tzinfo=timezone.utc)
# corresponds to v0.2.0 release
SUNSET_DATE = datetime(2025, 8, 30, 23, 59, 59, tzinfo=timezone.utc)

app = FastAPI()
app.include_router(users_router.router)
# all routes from this router are deprecated as of v0.2.0
app.include_router(llm_router.router)
# all routes from this router are deprecated as of v0.3.0
app.include_router(status_router.router)


# importing secrets from the .env file
settings = get_settings()
if not settings.openai_api_key:
    raise RuntimeError("OPENAI_API_KEY is required to call the LLM.")
if not settings.db_url:
    raise RuntimeError("DB_URL is required to run the server.")

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
async def root() -> None:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="GET / has been retired. It may return in the future.",
        headers={
            # this is an emerging standard. expects either "true" or a HTTP-date timestamp
            "Deprecation": format_datetime(DEPRECATION_DATE, usegmt=True),
            # this returns a HTTP-date timestamp, which is expected according to RFC 8594 (source: https://datatracker.ietf.org/doc/html/rfc8594)
            "Sunset": format_datetime(SUNSET_DATE, usegmt=True)
        }
    )


# helper function that calls a OpenAI LLM to analyze dependencies and returns a structured output
async def get_llm_analysis(
    project_name: str,
    reqs: list[str]
) -> Optional[AnalysisResult]:
    """
    Runs in a FastAPI BackgroundTask. Calls the LLM via LangChain with structured output. Returns the `AnalysisResult`. On error, returns `None`.
    """
    try:
        # bind the Pydantic output schema directly to the LLM
        structured_llm = llm.with_structured_output(AnalysisResult)

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

        result: AnalysisResult = AnalysisResult.model_validate(await structured_llm.ainvoke(messages))
        return result

    except Exception as e:
        print(
            f"[{datetime.now()}] get_llm_analysis failed for {project_name}: {e}")
        return None


@app.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
)
async def analyze_dependencies(
    file: Annotated[UploadFile, File(
        description="A requirements.txt file (text/plain).")],
    project_name: Annotated[str, Form(
        description="The name of the project")],
    user: Annotated[UserPublic, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
) -> AnalyzeResponse:
    """
    Accepts a requirements.txt file upload and a project name, analyzes each license associated with the dependencies in the 'requirements.txt' file, and returns the analysis.

    Throws a 400 if the uploaded file is empty.

    Throws a 401 if the user is unauthorized.

    Throws a 415 if the uploaded file has an unsupported MIME type.

    Throws a 422 if:
     - the project name is less than 1 or greater than 100 characters.
     - the uploaded file does not have a .txt extension.
     - there is a Unicode decode error while processing the file.
     - the requirements.txt file is invalid and cannot be parsed.
     - no valid requirements are found in the file.

    Keyword arguments:

    file -- an non-empty 'requirements.txt'

    project_name -- the name of your project
    """
    if len(project_name) < 1 or len(project_name) > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Project name must be between 1 and 100 characters."
        )

    # log event (project creation) in the database
    requirements_content: str = (await file.read()).decode("utf-8")
    await add_event(
        session,
        Event(
        user_id=user.id,
        project_name=project_name,
        event=EventType.PROJECT_CREATED,
        content=requirements_content
    ))

    # always make sure to reset the file pointer after reading!
    await file.seek(0)
    try:
        await validate_requirements_file(file)  # validate the file
    except HTTPException as e:
        # if the validation failed for any reason, log event (validation failed) in the database
        await add_event(
            session,
            Event(
                user_id=user.id,
                project_name=project_name,
                event=EventType.VALIDATION_FAILED,
            )
        )
        raise e

    # always make sure to reset the file pointer after reading!
    await file.seek(0)
    _reqs = await parse_requirements_file(file)  # parse requirements from file
    # log event (validation success) in the database
    await add_event(
        session,
        Event(
            user_id=user.id,
            project_name=project_name,
            event=EventType.VALIDATION_SUCCESS,
            content=", ".join(_reqs)
        )
    )

    # log event (analysis started) in the database
    await add_event(
        session,
        Event(
            user_id=user.id,
            project_name=project_name,
            event=EventType.ANALYSIS_STARTED
        )
    )
    # retrieve the analysis from the LLM
    project_id = uuid4()
    llm_result = await get_llm_analysis(project_name, _reqs)

    # log event (either analysis completion or failure) in the database
    await add_event(
        session,
        Event(
            user_id=user.id,
            project_name=project_name,
            event=EventType.ANALYSIS_COMPLETED if llm_result else EventType.ANALYSIS_FAILED,
            content=llm_result.model_dump_json() if llm_result else None
        )
    )
    return AnalyzeResponse(
        project_id=project_id,
        status=Status.COMPLETED if llm_result else Status.FAILED,
        result=llm_result
    )
