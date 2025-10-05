from sqlmodel.ext.asyncio.session import AsyncSession
from crud.events import upsert_event, select_project_events
from srv.schemas import Event


async def add_event(session: AsyncSession, event: Event) -> None:
    """
    Business logic to add a new event.
    """
    await upsert_event(session, event)


async def list_events(session: AsyncSession, user_id: str, project_name: str) -> list[Event]:
    """
    Given a `user_id` and a valid `project_name`, this will return a list of `Event`s stored in the database.
    """
    events = await select_project_events(session, user_id, project_name)
    return events
