from fastapi import status
from conftest import BASE64URL

FORM_HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}


def test_check_response_format(client):
    """Tests the format of the "POST /users/token" response."""
    data = {"username": "johndoe", "password": "secret"}
    r = client.post("/users/token", data=data, headers=FORM_HEADERS)
    assert r.status_code == status.HTTP_200_OK, r.text
    body = r.json()

    # check response fields
    assert "token_type" in body and isinstance(body["token_type"], str)
    assert "access_token" in body and isinstance(body["access_token"], str)


def test_success_with_valid_credentials(client):
    """Tests that POST /users/token returns a bearer token for valid credentials."""
    data = {"username": "johndoe", "password": "secret"}
    r = client.post("/users/token", data=data, headers=FORM_HEADERS)
    assert r.status_code == status.HTTP_200_OK, r.text
    body = r.json()
    token = body["access_token"]

    assert body["token_type"] == "bearer"
    # all valid JWTs are 3 Base64URL strings separated by dots
    assert token.count(".") == 2    # 3 Base64URL strings = 2 dots
    for b64 in token.split("."):
        assert BASE64URL.match(b64)


def test_rejects_wrong_password(client):
    """Tests that an incorrect password results in a 401 error."""
    data = {"username": "johndoe", "password": "WRONG"}
    r = client.post("/users/token", data=data, headers=FORM_HEADERS)
    assert r.status_code == status.HTTP_401_UNAUTHORIZED
    assert "incorrect username or password" in r.text.lower()
    assert r.headers.get("www-authenticate", "").lower() == "bearer"


def test_rejects_unknown_user(client):
    """Tests that an unknown user results in a 401 error."""
    data = {"username": "ghost", "password": "secret"}
    r = client.post("/users/token", data=data, headers=FORM_HEADERS)
    assert r.status_code == status.HTTP_401_UNAUTHORIZED
    assert "incorrect username or password" in r.text.lower()
