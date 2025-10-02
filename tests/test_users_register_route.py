import copy
import pytest
from fastapi import HTTPException, status
from conftest import HEX32


def _payload(username="newuser"):
    return {
        "username": username,
        "password": "supersecret",
        "email": "newuser@example.com",
        "full_name": "New User",
    }


def test_check_response_format(client_with_seed):
    """Tests the format of the "POST /users/" response."""
    r = client_with_seed.post("/users/", json=_payload())
    assert r.status_code == status.HTTP_201_CREATED, r.text
    body = r.json()

    # check response fields
    assert "id" in body and isinstance(body["id"], str)
    assert "username" in body and isinstance(body["username"], str)
    assert "full_name" in body and isinstance(body["full_name"], str)
    assert "email" in body and isinstance(body["email"], str)
    assert "hashed_password" not in body
    assert "password" not in body


def test_success_create_new_user(client_with_seed):
    """Tests that "POST /users/" creates a new user."""
    r = client_with_seed.post("/users/", json=_payload())
    assert r.status_code == status.HTTP_201_CREATED, r.text
    body = r.json()

    assert HEX32.match(body["id"])
    assert body["username"] == "newuser"
    assert "hashed_password" not in body
    assert "password" not in body


def test_rejects_already_preexisting_username(client_with_seed):
    """Tests that a duplicate username results in a 400 error."""
    r = client_with_seed.post("/users/", json=_payload(username="seeded"))
    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert "already registered" in r.text.lower()


def test_rejects_invalid_body(client_with_seed):
    """Tests that bad request bodies results in a 422 error."""
    r = client_with_seed.post("/users/", json={"username": "x"})
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_rejects_password_too_short(client_with_seed):
    r = client_with_seed.post("/users/", json={"username": "seeded", "password": ""})
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "string should have at least 4 characters" in r.text.lower()


def test_create_user_rejects_username_too_short(client_with_seed):
    r = client_with_seed.post("/users/", json={"username": "jon", "password": "test"})
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "string should have at least 4 characters" in r.text.lower()


def test_create_user_rejects_username_too_long(client_with_seed):
    r = client_with_seed.post(
        "/users/", json={"username": "a" * 101, "password": "test"})
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "string should have at most 100 characters" in r.text.lower()
