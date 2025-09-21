import copy
from pydantic import ValidationError
import pytest
from crud import users as users_crud
from db.db import FAKE_USERS_DB
from srv.schemas import User, UserCreate


@pytest.fixture(autouse=True)
def _reset_users_table():
    snapshot = copy.deepcopy(FAKE_USERS_DB)
    try:
        yield
    finally:
        FAKE_USERS_DB.clear()
        FAKE_USERS_DB.update(snapshot)


def test_get_user_success_when_user_is_present():
    """Tests that `get_user()` returns a User when present."""
    u = users_crud.get_user("johndoe")
    assert u is not None
    assert type(u) is User
    assert u.username == "johndoe"


def test_get_user_returns_none_when_missing():
    """Tests that `get_user()` returns None for unknown usernames."""
    assert users_crud.get_user("nobody") is None


def test_authenticate_user_success_when_correct_credentials():
    """Tests that `authenticate_user()` returns a User for correct credentials."""
    u = users_crud.authenticate_user("johndoe", "secret")
    assert u is not None
    assert type(u) is User
    assert u.username == "johndoe"


def test_authenticate_user_returns_none_when_wrong_password():
    """Tests that `authenticate_user()` returns None for wrong password."""
    assert users_crud.authenticate_user("johndoe", "WRONG") is None


def test_authenticate_user_returns_none_when_user_unknown():
    """Tests that `authenticate_user()` returns None for unknown user."""
    assert users_crud.authenticate_user("ghost", "secret") is None


def test_create_user_hashes_password_and_persists_users(monkeypatch):
    """Tests that `create_user()` hashes the password and persists the user."""
    # NOTE: we say "crud.users.get_hashed_pwd" instead of "srv.security.get_hashed_pwd" here because "crud.users" IMPORTS 
    # `get_hashed_pwd()`, becoming "a part of" its list of functions that we can call
    # To put this simply: if we DON'T do this, then it'll call the version of `get_hashed_pwd()` from the "security" package 
    # and NOT our mocked version!
    # source: https://stackoverflow.com/a/64161240
    monkeypatch.setattr("crud.users.get_hashed_pwd", lambda _: "hashed:xyz")
    created = users_crud.create_user(
        UserCreate(username="alice", password="test", full_name="Alice Lastname", email="alice@example.com")
    )
    assert created.username == "alice"
    assert created.full_name == "Alice Lastname"
    assert created.email == "alice@example.com"
    u = FAKE_USERS_DB.get("alice")
    assert u is not None
    assert "hashed_password" in u and isinstance(u["hashed_password"], str)
    assert u["hashed_password"] != "test"
    assert u["hashed_password"] == "hashed:xyz"
    assert "password" not in u


def test_create_user_rejects_password_too_short():
    with pytest.raises(ValidationError) as ex:
        users_crud.create_user(
            UserCreate(username="alice", password="", full_name="", email="")
        )
    assert "string should have at least 4 characters" in str(ex.value).lower()


def test_create_user_rejects_username_too_short():
    with pytest.raises(ValidationError) as ex:
        users_crud.create_user(
            UserCreate(username="jon", password="test", full_name="", email="")
        )
    assert "string should have at least 4 characters" in str(ex.value).lower()


def test_create_user_rejects_username_too_long():
    with pytest.raises(ValidationError) as ex:
        users_crud.create_user(
            UserCreate(username="a" * 101, password="test",
                       full_name="", email="")
        )
    assert "string should have at most 100 characters" in str(ex.value).lower()
