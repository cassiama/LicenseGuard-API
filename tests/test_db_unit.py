import uuid
import pytest
from conftest import HEX32
from srv.schemas import Event, EventType, UserCreate, UserPublic
from crud.events import add_event, get_project_events
from services.users import get_user, create_user


@pytest.mark.asyncio(loop_scope="session")
async def test_event_add_and_filter(session_override):
    """Tests that the provided SQLAlchemy session stores events and filters by project/user."""
    u1_id = uuid.uuid4()
    await add_event(
        session_override,
        Event(
            user_id=u1_id,
            project_name="p1",
            event=EventType.PROJECT_CREATED
        )
    )
    await add_event(
        session_override,
        Event(
            user_id=u1_id,
            project_name="p2",
            event=EventType.PROJECT_CREATED
        )
    )
    events = await get_project_events(session_override, u1_id, "p1")
    assert len(events) == 1
    e1 = events[0]
    assert e1.user_id == u1_id and HEX32.match(str(u1_id))
    assert e1.project_name == "p1"
    assert e1.event == EventType.PROJECT_CREATED
    assert e1.content is None
    events = await get_project_events(session_override, u1_id, "p2")
    assert len(events) == 1
    e2 = events[0]
    assert e2.user_id == u1_id and HEX32.match(str(u1_id))
    assert e2.project_name == "p2"
    assert e2.event == EventType.PROJECT_CREATED
    assert e2.content is None


@pytest.mark.asyncio(loop_scope="session")
async def test_get_user_by_username_and_create_user_roundtrip(session_override):
    """Tests `create_user()` and `get_user()` work together."""
    # verify that it returns nothing if the user doesn't exist
    ghost = await get_user(session_override, "ghost")
    assert ghost is None

    u = UserCreate(
        username="alice", full_name="Alice in Wonderland", email="alice@example.com",
        password="secret",
    )
    saved = await create_user(session_override, u)
    # verify that saving the user worked
    assert saved is not None and isinstance(saved, UserPublic)
    assert HEX32.match(str(saved.id))
    assert saved.username == "alice"
    assert saved.full_name == "Alice in Wonderland"
    assert saved.email == "alice@example.com"

    # verify that the password wasn't exposed (even though we confirmed above that it should be a
    # UserPublic model)
    obj = saved.model_dump_json()
    assert "password" not in obj
    assert "hashed_password" not in obj

    # verify that the user has been found and has the same attributes as the one we saved before
    found = await get_user(session_override, "alice")
    assert found is not None and isinstance(found, UserPublic)
    assert found.id == saved.id
    assert found.username == saved.username
    assert found.full_name == saved.full_name
    assert found.email == saved.email
    # although we confirmed that this is a UserPublic model and it seems to have all of the same attributes, we should still ensure that password is NEVER exposed!
    obj = found.model_dump_json()
    assert "password" not in obj
    assert "hashed_password" not in obj
