import pytest
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager
from srv.app import app
from srv.schemas import UserPublic


@pytest.mark.asyncio
async def test_register_login_and_me():
    async with LifespanManager(app):    # fires off startup/shutdown
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            # first, we register a user
            # GOAL: verify `services.users.create_user()` works as intended
            register_resp = await c.post("/users/", json={
                "username": "basic",
                "password": "test123",
                "email": "basic@example.com",
                "full_name": "Basic User"
            })
            assert register_resp.status_code == 201, register_resp.text
            
            # verify that the object returned in the response is a valid `UserPublic` object
            import json
            u = UserPublic.model_validate(json.loads(register_resp.text))
            assert isinstance(u, UserPublic)

            # next, we get a token from /users/token
            # GOAL: verify `create_access_token()` returns a JWT via OAuth2PasswordRequestForm
            token_resp = await c.post(
                "/users/token", data={"username": "basic", "password": "test123"})
            assert token_resp.status_code == 200, token_resp.text
            token_json = token_resp.json()
            assert "access_token" in token_json
            token = token_json["access_token"]

            # finally, verify that the current user's info by calling "/users/me" with the token
            # GOAL: verify `get_current_user()` works as intended
            me_resp = await c.get("/users/me", headers={"Authorization": f"Bearer {token}"})
            assert me_resp.status_code == 200, me_resp.text  # protected by get_current_user
            body = me_resp.json()
            assert body["username"] == "basic"
