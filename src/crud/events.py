from datetime import datetime
from uuid import UUID
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from srv.schemas import Event


async def upsert_event(session: AsyncSession, project_evt: Event) -> None:
    """
    Upsert a new event into the database.
    """
    print(
        f"[{datetime.now()}]: {project_evt.event} for project {project_evt.project_name}.")

    session.add(project_evt)
    await session.commit()
    await session.refresh(project_evt)


async def get_events_list(session: AsyncSession, user_id: UUID, project_name: str) -> list[Event]:
    """
    Filters the database to find all events for a specific project and user.
    """
    result = await session.exec(select(Event).where((Event.user_id == user_id) & (Event.project_name == project_name)))
    rows = result.all()
    events = []
    for r in rows:
        events.append(
            Event(
                id=r.id,
                user_id=r.user_id,
                project_name=r.project_name,
                event=r.event,
                timestamp=r.timestamp,
                content=r.content
            )
        )
    return events
