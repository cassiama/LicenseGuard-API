from datetime import datetime, timezone
from email.utils import format_datetime
from fastapi import APIRouter, HTTPException, Response, status

# corresponds to commit 9ac8af3
DEPRECATION_DATE = datetime(2025, 8, 30, 17, 43, 17, tzinfo=timezone.utc)
# corresponds to v0.3.0 release
SUNSET_DATE = datetime(2025, 9, 20, 23, 59, 59, tzinfo=timezone.utc)

router = APIRouter(prefix="/status", tags=["status"])

# this route has been deprecated as of v0.3.0
@router.get(
    "/{project_id}",
    status_code=status.HTTP_410_GONE,
    deprecated=True
)
async def get_progress(
    project_id: str
) -> None:
    """
    NOTE: This route has been deprecated as of v0.3.0.

    Always returns a 410 with deprecation headers.

    Keyword arguments:

    project_id (unused) -- a valid UUIDv4 corresponding to a valid project_id
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="GET /status/{project_id} has been retired.",
        headers={
            # this is an emerging standard. expects either "true" or a HTTP-date timestamp
            "Deprecation": format_datetime(DEPRECATION_DATE, usegmt=True),
            # this returns a HTTP-date timestamp, which is expected according to RFC 8594 (source: https://datatracker.ietf.org/doc/html/rfc8594)
            "Sunset": format_datetime(SUNSET_DATE, usegmt=True)
        }
    )
