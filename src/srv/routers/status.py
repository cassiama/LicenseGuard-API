from fastapi import APIRouter, Depends, HTTPException, status
from db.db import get_db, DBClient
from ..schemas import StatusResponse

router = APIRouter(prefix="/status", tags=["status"])

# this route has been deprecated as of v0.3.0
@router.get(
    "/{project_id}",
    response_model=StatusResponse,
    status_code=status.HTTP_200_OK,
    deprecated=True
)
async def get_progress(
    project_id: str,
    db: DBClient = Depends(get_db)
) -> StatusResponse:
    """
    Returns the status and (if present) result for a given project_id.

    Throws a 404 if the project_id does not exist.

    Keyword arguments:

    project_id -- a valid UUIDv4 corresponding to a valid project_id
    """
    record = await db.get_project(project_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found."
        )

    return StatusResponse(
        project_id=record.id,
        status=record.status,
        result=record.result,
        # timestamp field in StatusResponse will auto-populate via its default factory
    )
