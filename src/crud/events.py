from datetime import datetime
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from srv.schemas import Event


async def upsert_event(session: AsyncSession, logged_evt: Event) -> None:
    """
    Upsert/log a new event into the database.
    """
    print(
        f"[{datetime.now()}]: Logging event type \"{logged_evt.event}\" for project \"{logged_evt.project_name}\".")

    session.add(logged_evt)
    await session.commit()
    await session.refresh(logged_evt)


async def select_project_events(session: AsyncSession, user_id: str, project_name: str) -> list[Event]:
    """
    Filters the database to find all logged events for a specific project and user.
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
