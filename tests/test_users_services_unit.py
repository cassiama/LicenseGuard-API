import pytest
from pydantic import ValidationError
from db.session import get_db
from services.users import authenticate_user, create_user, get_user
from crud.users import get_user_by_username
from srv.schemas import UserPublic, UserCreate


async def test_get_user_success_when_user_is_present():
    """Tests that `get_user()` returns a UserPublic when present."""
    session = get_db()
    u = await get_user(session, "johndoe")
    assert u is not None
    assert type(u) is UserPublic
    assert u.username == "johndoe"


async def test_get_user_returns_none_when_missing():
    """Tests that `get_user()` returns None for unknown usernames."""
    session = get_db()
    u = await get_user(session, "nobody")
    assert u is None


async def test_authenticate_user_success_when_correct_credentials():
    """Tests that `authenticate_user()` returns a UserPublic for correct credentials."""
    session = get_db()
    u = await authenticate_user(session, "johndoe", "secret")
    assert u is not None
    assert type(u) is UserPublic
    assert u.username == "johndoe"


async def test_authenticate_user_returns_none_when_wrong_password():
    """Tests that `authenticate_user()` returns None for wrong password."""
    session = get_db()
    u = await authenticate_user(session, "johndoe", "WRONG")
    assert u is None


async def test_authenticate_user_returns_none_when_user_unknown():
    """Tests that `authenticate_user()` returns None for unknown user."""
    session = get_db()
    u = await authenticate_user(session, "ghost", "secret")
    assert u is None


async def test_create_user_hashes_password_and_persists_users(monkeypatch):
    """Tests that `create_user()` hashes the password and persists the user."""
    session = get_db()
    # NOTE: we say "crud.users.get_hashed_pwd" instead of "srv.security.get_hashed_pwd" here 
    # because "crud.users" IMPORTS `get_hashed_pwd()`, becoming "a part of" its list of functions 
    # that we can call
    # To put this simply: if we DON'T do this, then it'll call the version of `get_hashed_pwd()` from the "security" package
    # and NOT our mocked version!
    # source: https://stackoverflow.com/a/64161240
    monkeypatch.setattr("crud.users.get_hashed_pwd", lambda _: "hashed:xyz")
    created = await create_user(
        session,
        UserCreate(username="alice", password="test",
                   full_name="Alice Lastname", email="alice@example.com")
    )
    assert created.username == "alice"
    assert created.full_name == "Alice Lastname"
    assert created.email == "alice@example.com"
    u = await get_user_by_username(session, "alice")
    assert u is not None
    obj = u.model_dump_json()
    assert "hashed_password" in obj and isinstance("hashed_password", str)
    assert u.hashed_password != "test"
    assert u.hashed_password == "hashed:xyz"
    assert "password" not in obj


async def test_create_user_rejects_password_too_short():
    session = get_db()
    with pytest.raises(ValidationError) as ex:
        await create_user(
            session,
            UserCreate(username="alice", password="", full_name="", email="")
        )
    assert "string should have at least 4 characters" in str(ex.value).lower()


async def test_create_user_rejects_username_too_short():
    session = get_db()
    with pytest.raises(ValidationError) as ex:
        await create_user(
            session,
            UserCreate(username="jon", password="test", full_name="", email="")
        )
    assert "string should have at least 4 characters" in str(ex.value).lower()


async def test_create_user_rejects_username_too_long():
    session = get_db()
    with pytest.raises(ValidationError) as ex:
        create_user(
            session,
            UserCreate(username="a" * 101, password="test",
                       full_name="", email="")
        )
    assert "string should have at most 100 characters" in str(ex.value).lower()
