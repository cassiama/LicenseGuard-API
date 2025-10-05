import pytest
from uuid import uuid4
from datetime import datetime, timezone
from conftest import HEX32
from srv.schemas import Event, EventType
from services.events import add_event, list_events


@pytest.mark.asyncio(loop_scope="session")
async def test_event_add_and_filter(session_override):
    """Tests that the provided SQLAlchemy session stores events and filters by project/user."""
    u1_id = str(uuid4())
    await add_event(
        session_override,
        Event(
            user_id=u1_id,
            project_name="p1",
            event=EventType.PROJECT_CREATED,
            timestamp=datetime.now(timezone.utc)
        )
    )
    await add_event(
        session_override,
        Event(
            user_id=u1_id,
            project_name="p2",
            event=EventType.PROJECT_CREATED,
            timestamp=datetime.now(timezone.utc)
        )
    )
    events = await list_events(session_override, u1_id, "p1")
    assert len(events) == 1
    e1 = events[0]
    assert e1.user_id == u1_id and HEX32.match(str(u1_id))
    assert e1.project_name == "p1"
    assert e1.event == EventType.PROJECT_CREATED
    assert e1.content is None
    events = await list_events(session_override, u1_id, "p2")
    assert len(events) == 1
    e2 = events[0]
    assert e2.user_id == u1_id and HEX32.match(str(u1_id))
    assert e2.project_name == "p2"
    assert e2.event == EventType.PROJECT_CREATED
    assert e2.content is None
