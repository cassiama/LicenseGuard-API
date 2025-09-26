import uuid
import pytest
from fastapi import FastAPI
from db.db import (
    MockDBClient, RealDBClient, create_db_client, lifespan, get_user_by_username, save_user
)
from srv.schemas import Event, EventType, User
from srv.security import get_hashed_pwd
from conftest import HEX32


@pytest.mark.asyncio
async def test_mockdbclient_upsert_and_filter():
    """Tests that MockDBClient stores events and filters by project/user."""
    db = MockDBClient()
    await db.connect()
    u1_id = uuid.uuid4()
    await db.upsert_event(Event(
        user_id=u1_id,
        project_name="p1",
        event=EventType.PROJECT_CREATED
    ))
    await db.upsert_event(Event(
        user_id=u1_id,
        project_name="p2",
        event=EventType.PROJECT_CREATED
    ))
    events = await db.get_project_events(u1_id, "p1")
    assert len(events) == 1
    e1 = events[0]
    assert e1.user_id == u1_id and HEX32.match(str(u1_id))
    assert e1.project_name == "p1"
    assert e1.event == EventType.PROJECT_CREATED
    assert e1.content is None
    events = await db.get_project_events(u1_id, "p2")
    assert len(events) == 1
    e2 = events[0]
    assert e2.user_id == u1_id and HEX32.match(str(u1_id))
    assert e2.project_name == "p2"
    assert e2.event == EventType.PROJECT_CREATED
    assert e2.content is None
    await db.disconnect()


def test_create_db_client_uses_real_if_DB_URL(monkeypatch):
    """Tests that `create_db_client()` returns RealDBClient when DB_URL is set."""
    monkeypatch.setenv("DB_URL", "postgresql://example")
    db = create_db_client()
    assert isinstance(db, RealDBClient)


def test_create_db_client_defaults_to_mock(monkeypatch):
    """Tests that `create_db_client()` returns MockDBClient when DB_URL is missing."""
    monkeypatch.delenv("DB_URL", raising=False)
    db = create_db_client()
    assert isinstance(db, MockDBClient)


@pytest.mark.asyncio
async def test_lifespan_binds_and_unbinds_db():
    """Tests that lifespan context attaches and clears app.state.db."""
    app = FastAPI()
    # once the lifespan context starts, the DB should be bound
    async with lifespan(app):
        assert getattr(app.state, "db", None) is not None
    # now that lifespan context is over, the DB should be unbound
    assert getattr(app.state, "db", None) is None


def test_get_user_by_username_and_save_user_roundtrip():
    """Tests `save_user()` and `get_user_by_username()` work together."""
    assert get_user_by_username("ghost") is None
    u = User(
        username="alice", full_name="", email="",
        hashed_password=get_hashed_pwd("pw"),
    )
    saved = save_user(u)
    assert type(saved) is User
    assert HEX32.match(str(saved.id))
    assert saved.username == "alice"
    assert saved.hashed_password is not None
    assert get_user_by_username("alice") is not None
