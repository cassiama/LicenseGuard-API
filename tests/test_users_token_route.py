from fastapi import status
from conftest import BASE64URL

FORM_HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}


def test_check_response_format(monkeypatch, client_with_seed):
    """Tests the format of the "POST /users/token" response."""
    # NOTE: we say "services.users.verify_pwd" instead of "srv.security.verify_pwd"
    # here because "services.users" IMPORTS `verify_pwd()`, becoming "a part of" its
    # list of functions that we can call.
    # To put this simply: if we DON'T do this, then it'll call the version of `verify_pwd()` 
    # from the "security" package and NOT our mocked version!
    # source: https://stackoverflow.com/a/64161240
    monkeypatch.setattr("services.users.verify_pwd", lambda x, y: x == y)
    data = {"username": "seeded", "password": "secret"}
    r = client_with_seed.post("/users/token", data=data, headers=FORM_HEADERS)
    assert r.status_code == status.HTTP_200_OK, r.text
    body = r.json()

    # check response fields
    assert "token_type" in body and isinstance(body["token_type"], str)
    assert "access_token" in body and isinstance(body["access_token"], str)


def test_success_with_valid_credentials(monkeypatch, client_with_seed):
    """Tests that POST /users/token returns a bearer token for valid credentials."""
    # NOTE: we say "services.users.verify_pwd" instead of "srv.security.verify_pwd"
    # here because "services.users" IMPORTS `verify_pwd()`, becoming "a part of" its
    # list of functions that we can call.
    # To put this simply: if we DON'T do this, then it'll call the version of `verify_pwd()` 
    # from the "security" package and NOT our mocked version!
    # source: https://stackoverflow.com/a/64161240
    monkeypatch.setattr("services.users.verify_pwd", lambda x, y: x == y)
    data = {"username": "seeded", "password": "secret"}
    r = client_with_seed.post("/users/token", data=data, headers=FORM_HEADERS)
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
    data = {"username": "seeded", "password": "WRONG"}
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
