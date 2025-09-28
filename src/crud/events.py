from datetime import datetime
from uuid import UUID
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from srv.schemas import Event


async def add_event(session: AsyncSession, project_ev: Event) -> None:
    """
    Adds a new event to the database.
    """
    print(
        f"[{datetime.now()}]: {project_ev.event} for project {project_ev.project_name}.")

    session.add(project_ev)
    await session.commit()
    await session.refresh(project_ev)


async def get_project_events(session: AsyncSession, user_id: UUID, project_name: str) -> list[Event]:
    """
    Filters the database to find all events for a specific project and user.
    """
    result = await session.execute(select(Event).where(Event.user_id == user_id and Event.project_name == project_name))
    rows = result.scalars().all()
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
