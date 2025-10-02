import pytest
from fastapi import status
from fastapi.testclient import TestClient
from conftest import HEX32
from srv.app import app
from srv.security import create_access_token


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_check_response_format_conftest_auto_auth(client):
    """Tests the format of the "GET /users/me" response (uses the automatically authenticated user from "conftest")."""
    r = client.get("/users/me")
    assert r.status_code == status.HTTP_200_OK, r.text
    body = r.json()

    # check response fields
    assert "id" in body and isinstance(body["id"], str)
    assert "username" in body and isinstance(body["username"], str)
    assert "full_name" in body and isinstance(body["full_name"], str)
    assert "email" in body and isinstance(body["email"], str)
    assert "hashed_password" not in body
    assert "password" not in body


def test_accepts_conftest_auto_auth(client):
    """Tests that the response from "GET /users/me" returns the automatically authenticated user from "conftest"."""
    r = client.get("/users/me")
    assert r.status_code == status.HTTP_200_OK, r.text
    body = r.json()
    # provided by conftest override
    assert HEX32.match(str(body["id"]))
    assert body["username"] == "testuser"
    assert body["full_name"] == "Test User"
    assert body["email"] == "testuser@example.org"
    assert "hashed_password" not in body
    assert "password" not in body


@pytest.mark.asyncio
async def test_check_response_format_with_real_token(client_with_seed):
    """Tests that GET /users/me works with a real token when dependency override is cleared."""
    from srv.security import get_current_user

    # we only need to keep the "get_session" override; everything else needs to be cleared
    app.dependency_overrides.pop(get_current_user, None)

    token = create_access_token({"sub": "seeded"})
    r = client_with_seed.get("/users/me", headers=_bearer(token))
    assert r.status_code == status.HTTP_200_OK, r.text
    body = r.json()

    # check response fields
    assert "id" in body and isinstance(body["id"], str)
    assert "username" in body and isinstance(body["username"], str)
    assert "full_name" in body and isinstance(body["full_name"], str)
    assert "email" in body and isinstance(body["email"], str)
    assert "hashed_password" not in body
    assert "password" not in body


@pytest.mark.asyncio
async def test_success_with_real_token(client_with_seed):
    """Tests that the response from "GET /users/me" works with a real token and returns a valid UserPublic."""
    from srv.security import get_current_user

    # we only need to keep the "get_session" override; everything else needs to be cleared
    app.dependency_overrides.pop(get_current_user, None)

    token = create_access_token({"sub": "seeded"})
    r = client_with_seed.get("/users/me", headers=_bearer(token))
    assert r.status_code == status.HTTP_200_OK, r.text
    body = r.json()

    assert HEX32.match(body["id"])
    assert body["username"] == "seeded"
    assert "hashed_password" not in body
    assert "password" not in body


def test_rejects_missing_authorization_header():
    """Tests that a missing Authorization header results in a 401 error."""
    app.dependency_overrides.clear()
    with TestClient(app) as raw_resp:
        r = raw_resp.get("/users/me")
        assert r.status_code == status.HTTP_401_UNAUTHORIZED
        assert "not authenticated" in r.text.lower()
