from typing import Annotated
from datetime import datetime
from uuid import uuid4
from fastapi import FastAPI, UploadFile, File, Depends, status
from fastapi.exceptions import RequestValidationError
from db.db import DBClient, get_db, lifespan
from .schemas import AnalyzeResponse, ProjectRecord, Status
from .routers import llm, status as status_router
from .validators import validate_requirements_file

app = FastAPI(lifespan=lifespan)
# all routes from this router are deprecated as of v0.2.0
app.include_router(llm.router)
app.include_router(status_router.router)


# this route is deprecated as of v0.2.0 (might be reenabled later on, we'll see!)
@app.get("/", deprecated=True)
async def root():
    return {"message": "Hello World!"}


@app.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def analyze_dependencies(
    file: Annotated[UploadFile, File(
        description="A requirements.txt file (text/plain).")],
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
    return AnalyzeResponse(
        project_id=project_id,
        status=Status.IN_PROGRESS,
        result=None
    )
