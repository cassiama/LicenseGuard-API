import pytest
import jwt
from datetime import timedelta
from fastapi import HTTPException
from conftest import BASE64URL
from core.config import Settings
from srv.schemas import User
from srv.security import verify_pwd, get_hashed_pwd, create_access_token, get_current_user

settings = Settings()


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

    payload = jwt.decode(token, str(settings.jwt_secret_key),
                         algorithms=[settings.jwt_algorithm])
    assert payload.get("sub") == "johndoe"
    assert "exp" in payload


def test_get_valid_user_for_valid_token():
    """Tests that `get_current_user()` returns a User for a valid token."""
    token = create_access_token({"sub": "johndoe"})
    user = get_current_user(token)
    assert type(user) is User
    assert user.username == "johndoe"


def test_get_current_user_raises_exception_on_expired_token():
    """Tests that `get_current_user()` raises a 401 error on expired tokens."""
    token = create_access_token(
        {"sub": "johndoe"}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(HTTPException) as ex:
        get_current_user(token)
    assert ex.value.status_code == 401
    assert "could not validate user credentials" in str(
        ex.value.detail).lower()


def test_get_current_user_raises_exception_on_invalid_user(monkeypatch):
    """Tests that `get_current_user()` raises HTTP 401 when the user no longer exists."""
    monkeypatch.setattr("crud.users.get_user", lambda username: None)
    token = create_access_token({"sub": "ghost"})
    with pytest.raises(HTTPException) as ex:
        get_current_user(token)
    assert ex.value.status_code == 401
    assert "could not validate user credentials" in str(
        ex.value.detail).lower()
