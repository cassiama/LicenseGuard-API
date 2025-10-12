from uuid import uuid4
import pytest
import jwt
from datetime import timedelta
from fastapi import HTTPException
from unittest.mock import AsyncMock
from conftest import BASE64URL
from core.config import get_settings
from srv.schemas import UserPublic
from srv.security import verify_pwd, get_hashed_pwd, create_access_token, get_current_user

settings = get_settings()


def test_password_hash_and_verify():
    """Tests that hashing and verifying a password works."""
    hashed = get_hashed_pwd("pw123")
    assert isinstance(hashed, str)
    assert verify_pwd("pw123", hashed) is True
    assert verify_pwd("nope", hashed) is False


def test_produce_jwt_that_can_expire_and_is_decodable():
    """Tests that `create_access_token()` produces a decodable JWT with an expiration date."""
    token = create_access_token({"sub": "johndoe"})

    # all valid JWTs are 3 Base64URL strings separated by dots
    assert token.count(".") == 2    # 3 Base64URL strings = 2 dots
    for b64 in token.split("."):
        assert BASE64URL.match(b64)

    payload = jwt.decode(token, settings.jwt_secret_key.get_secret_value(),
                         algorithms=[settings.jwt_algorithm.get_secret_value()])
    assert payload.get("sub") == "johndoe"
    assert "exp" in payload


@pytest.mark.asyncio(loop_scope="session")
async def test_get_valid_user_for_valid_token(monkeypatch, session_override):
    """Tests that `get_current_user()` returns a UserPublic for a valid token."""
    token = create_access_token({"sub": "johndoe"})
    # in order for the test to pass, we need to mock the user lookup
    # otherwise, we would have to seed a DB
    monkeypatch.setattr(
        "services.users.get_user",
        AsyncMock(return_value=UserPublic(
            id=str(uuid4()), username="johndoe",))
    )
    user = await get_current_user(token, session_override)
    assert type(user) is UserPublic
    assert user.username == "johndoe"


@pytest.mark.asyncio(loop_scope="session")
async def test_get_current_user_raises_exception_on_expired_token(session_override):
    """Tests that `get_current_user()` raises a 401 error on expired tokens."""
    token = create_access_token(
        {"sub": "johndoe"}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(HTTPException) as ex:
        await get_current_user(token, session_override)
    assert ex.value.status_code == 401
    assert "could not validate user credentials" in str(
        ex.value.detail).lower()


@pytest.mark.asyncio(loop_scope="session")
async def test_get_current_user_raises_exception_on_invalid_user(monkeypatch, session_override):
    """Tests that `get_current_user()` raises HTTP 401 when the user no longer exists."""
    monkeypatch.setattr("services.users.get_user",
                        AsyncMock(return_value=None))
    token = create_access_token({"sub": "ghost"})
    with pytest.raises(HTTPException) as ex:
        await get_current_user(token, session_override)
    assert ex.value.status_code == 401
    assert "could not validate user credentials" in str(
        ex.value.detail).lower()
