from uuid import UUID
from sqlmodel.ext.asyncio.session import AsyncSession
from crud.events import upsert_event, get_events_list
from srv.schemas import Event


async def add_event(session: AsyncSession, project_evt: Event) -> None:
    """
    Business logic to add a new event.
    """
    await upsert_event(session, project_evt)


async def get_project_events(session: AsyncSession, user_id: UUID, project_name: str) -> list[Event]:
    """
    Given a `user_id` and a valid `project_name`, this will return a list of `Event`s stored in the database.
    """
    events = await get_events_list(session, user_id, project_name)
    return events
