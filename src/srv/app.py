from typing import Annotated
from uuid import uuid4
from fastapi import FastAPI, UploadFile, File, status
from fastapi.exceptions import RequestValidationError
from .schemas import AnalyzeResponse, Status
from .routers import llm, status as status_router
from .validators import validate_requirements_file

app = FastAPI()
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
        description="A requirements.txt file (text/plain).")]
) -> AnalyzeResponse:
    """
    Accepts a requirements.txt file upload, analyzes each license associated with the dependencies in the 'requirements.txt' file, and returns a new project.
    NOTE: Result is null until the analysis step is implemented.

    Keyword arguments:
    file -- an non-empty 'requirements.txt'
    """
    _reqs = await validate_requirements_file(file)  # validate & parse the requirements

    project_id = uuid4().hex
    return AnalyzeResponse(
        project_id=project_id,
        status=Status.IN_PROGRESS,
        result=None
    )
