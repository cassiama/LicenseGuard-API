from typing import Annotated, List
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Form
from core.config import get_settings
from srv.schemas import Token
from srv.security import create_access_token

router = APIRouter(prefix="/mcp", tags=["mcp"])

# use the name of the MCP server service user
MCP_SERVICE_USERNAME = "mcp-server"

# import the environment variables for the MCP server
settings = get_settings()
MCP_CLIENT_ID = settings.mcp_client_id
MCP_CLIENT_SECRET = settings.mcp_client_secret
JWT_AUDIENCE = settings.jwt_audience
MCP_ACCESS_TOKEN_EXPIRES_MINUTES = settings.mcp_access_token_expire_minutes
MCP_REQUIRED_SCOPES = settings.mcp_required_scopes


@router.post("/token", response_model=Token)
def issue_token(
    client_id: Annotated[str, Form()],
    client_secret: Annotated[str, Form()],
    scopes: Annotated[List[str] | None, Form()] = None,
):
    # verify that the MCP client ID and secret were provided
    if MCP_CLIENT_ID is None:
        raise RuntimeError(
            "MCP_CLIENT_ID is required to retrieve a JWT for the MCP server.")
    if MCP_CLIENT_SECRET is None:
        raise RuntimeError(
            "MCP_CLIENT_SECRET is required to retrieve a JWT for the MCP server.")

    # verify the MCP client ID and client secret
    if not client_id == MCP_CLIENT_ID and client_secret == MCP_CLIENT_SECRET:
        raise HTTPException(
            status_code=401, detail="MCP client has an invalid client ID or secret.")

    # get the scopes from the form data
    perms = " ".join(scopes) if scopes else ""
    required_scopes = MCP_REQUIRED_SCOPES.get_secret_value().split(" ")
    for scope in required_scopes:
        if scope not in perms:
            perms += f" {scope}"

    # create the payload for the JWT
    data = {
        "iss": "licenseguard-auth",  # TODO: change this to be the hostname of the API
        "sub": MCP_CLIENT_ID.get_secret_value(),   # MCP server's identity
        # who the token is intended for (i.e., the API)
        "aud": JWT_AUDIENCE.get_secret_value(),
        "scope": perms,    # permissions that the MCP server can use
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }

    # get the access token and return it
    access_token = create_access_token(
        data,
        timedelta(minutes=MCP_ACCESS_TOKEN_EXPIRES_MINUTES)
    )
    return Token(access_token=access_token, token_type="bearer")
