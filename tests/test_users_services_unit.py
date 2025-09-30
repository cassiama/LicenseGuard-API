import pytest
from uuid import uuid4
from pydantic import ValidationError
from services.users import authenticate_user, create_user, get_user
from services.users import get_user_by_username
from srv.schemas import User, UserPublic, UserCreate
from srv.security import get_hashed_pwd


@pytest.mark.asyncio
async def test_get_user_success_when_user_is_present(session_override):
    """Tests that `get_user()` returns a UserPublic when present."""
    from sqlalchemy import select, func
    from srv.schemas import User

    count = (await session_override.exec(select(func.count()).select_from(User))).one()
    print("DB user rows at start of test:", count)
    
    from sqlalchemy import text
    res = await session_override.exec(text("PRAGMA database_list"))  # if SQLite
    print("DB connection id:", id(await session_override.connection()))
    print("DB list:", res.all())

    # make sure to add the test user to the database before querying for it
    test_user = User(
        id=uuid4(),
        username="johndoe",
        hashed_password="totally-hashed-secret-password!"
    )
    session_override.add(test_user)
    await session_override.commit()
    await session_override.refresh(test_user)

    u = await get_user(session_override, "johndoe")
    assert u is not None
    assert type(u) is UserPublic
    assert u.username == "johndoe"


@pytest.mark.asyncio
async def test_get_user_returns_none_when_missing(session_override):
    """Tests that `get_user()` returns None for unknown usernames."""
    u = await get_user(session_override, "nobody")
    assert u is None


@pytest.mark.asyncio
async def test_authenticate_user_success_when_correct_credentials(monkeypatch, session_override):
    """Tests that `authenticate_user()` returns a UserPublic for correct credentials."""
    # NOTE: we say "services.users.verify_pwd" instead of "srv.security.verify_pwd"
    # here because "services.users" IMPORTS `verify_pwd()`, becoming "a part of" its
    # list of functions that we can call. As for "test_users_services_unit.get_hashed_pwd", 
    # we're changing the `get_hashed_pwd()` function that we imported into THIS FILE 
    # SPECIFICALLY.
    # To put this simply: if we DON'T do either of these, then it'll call the version of `get_hashed_pwd()` & `verify_pwd()` from the "security" package and NOT our mocked 
    # versions!
    # source: https://stackoverflow.com/a/64161240
    monkeypatch.setattr("test_users_services_unit.get_hashed_pwd",
                        lambda _: "hashed:xyz")
    monkeypatch.setattr("services.users.verify_pwd", lambda x, y: x == y)

    # make sure to add the test user to the database before querying for it
    test_user = User(
        id=uuid4(),
        username="johndoe",
        hashed_password=get_hashed_pwd("secret")
    )
    print(get_hashed_pwd("secret"))
    session_override.add(test_user)
    await session_override.commit()
    await session_override.refresh(test_user)

    u = await authenticate_user(session_override, "johndoe", get_hashed_pwd("secret"))
    assert u is not None
    assert type(u) is UserPublic
    assert u.username == "johndoe"


@pytest.mark.asyncio
async def test_authenticate_user_returns_none_when_wrong_password(session_override):
    """Tests that `authenticate_user()` returns None for wrong password."""
    u = await authenticate_user(session_override, "johndoe", "WRONG")
    assert u is None


@pytest.mark.asyncio
async def test_authenticate_user_returns_none_when_user_unknown(session_override):
    """Tests that `authenticate_user()` returns None for unknown user."""
    u = await authenticate_user(session_override, "ghost", "secret")
    assert u is None


@pytest.mark.asyncio
async def test_create_user_hashes_password_and_persists_users(monkeypatch, session_override):
    """Tests that `create_user()` hashes the password and persists the user."""
    # NOTE: we say "services.users.get_hashed_pwd" instead of "srv.security.get_hashed_pwd"
    # here because "services.users" IMPORTS `get_hashed_pwd()`, becoming "a part of" its
    # list of functions that we can call.
    # To put this simply: if we DON'T do this, then it'll call the version of `get_hashed_pwd()` 
    # from the "security" package and NOT our mocked version!
    # source: https://stackoverflow.com/a/64161240
    monkeypatch.setattr("services.users.get_hashed_pwd",
                        lambda _: "hashed:xyz")
    created = await create_user(
        session_override,
        UserCreate(username="alice", password="test",
                   full_name="Alice Lastname", email="alice@example.com")
    )
    assert created.username == "alice"
    assert created.full_name == "Alice Lastname"
    assert created.email == "alice@example.com"
    u = await get_user_by_username(session_override, "alice")
    assert u is not None
    obj = u.model_dump_json()
    assert "hashed_password" in obj and isinstance("hashed_password", str)
    assert u.hashed_password != "test"
    assert u.hashed_password == "hashed:xyz"
    assert obj.find("\"password\"") == -1


@pytest.mark.asyncio
async def test_create_user_rejects_password_too_short(session_override):
    with pytest.raises(ValidationError) as ex:
        await create_user(
            session_override,
            UserCreate(username="alice", password="", full_name="", email="")
        )
    assert "string should have at least 4 characters" in str(ex.value).lower()


@pytest.mark.asyncio
async def test_create_user_rejects_username_too_short(session_override):
    with pytest.raises(ValidationError) as ex:
        await create_user(
            session_override,
            UserCreate(username="jon", password="test", full_name="", email="")
        )
    assert "string should have at least 4 characters" in str(ex.value).lower()


@pytest.mark.asyncio
async def test_create_user_rejects_username_too_long(session_override):
    with pytest.raises(ValidationError) as ex:
        await create_user(
            session_override,
            UserCreate(username="a" * 101, password="test",
                       full_name="", email="")
        )
    assert "string should have at most 100 characters" in str(ex.value).lower()
