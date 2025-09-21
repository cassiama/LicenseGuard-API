from datetime import datetime, timezone
from email.utils import format_datetime
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

# corresponds to commit 3e7f2ac
DEPRECATION_DATE = datetime(2025, 8, 21, 23, 56, 46, tzinfo=timezone.utc)
# corresponds to v0.2.0 release
SUNSET_DATE = datetime(2025, 8, 30, 23, 59, 59, tzinfo=timezone.utc)

router = APIRouter(prefix="/llm", tags=["llm"])


# moved the Pydantic model for LLM prompts to this file so that the input to the route is the same
class LlmPrompt(BaseModel):
    body: str


@router.post("/guess", deprecated=True)
async def chat(
    body: LlmPrompt
) -> None:
    """
    NOTE: This route has been deprecated as of v0.3.0.

    Always returns a 410 with deprecation headers.

    Keyword arguments:

    body (unused) -- the prompt to the LLM
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="POST /llm/guess has been retired.",
        headers={
            # this is an emerging standard. expects either "true" or a HTTP-date timestamp
            "Deprecation": format_datetime(DEPRECATION_DATE, usegmt=True),
            # this returns a HTTP-date timestamp, which is expected according to RFC 8594 (source: https://datatracker.ietf.org/doc/html/rfc8594)
            "Sunset": format_datetime(SUNSET_DATE, usegmt=True)
        }
    )
