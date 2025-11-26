import jwt
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from sqlmodel.ext.asyncio.session import AsyncSession
from core.config import get_settings
from db.session import get_session
from srv.schemas import TokenData, UserPublic


# import the JWT config variables
settings = get_settings()
JWT_SECRET_KEY = settings.jwt_secret_key
JWT_ALGORITHM = settings.jwt_algorithm
# JWT_AUDIENCE = settings.jwt_audience
# MCP_CLIENT_ID = settings.mcp_client_id
# MCP_REQUIRED_SCOPES = settings.mcp_required_scopes

# setup password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# setup OAuth2 scheme for users; points to the login route
oauth2 = OAuth2PasswordBearer(tokenUrl="/users/token")


def verify_pwd(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_hashed_pwd(plain: str) -> str:
    return pwd_context.hash(plain)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    payload = data.copy()
    # if the user gave us an expiration date, use it
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    # otherwise, use the default (30 minutes)
    else:
        expire = datetime.now(
            timezone.utc) + timedelta(minutes=settings.user_access_token_expire_minutes)
    payload.update({"exp": expire})
    access_token = jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm.get_secret_value()
    )
    return access_token


# dependency for retrieving the current authenticated user
async def get_current_user(
    token: Annotated[str, Depends(oauth2)],
    session: Annotated[AsyncSession, Depends(get_session)]
) -> UserPublic:
    # import services here to avoid a circular dependency
    from services import users as users_service

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate user credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm.get_secret_value()]
        )
        username: str = payload.get("sub")
        if username is None:
            print("An username was not provided in the JWT!")
            raise credentials_exception

        # TODO: uncomment and refactor this when you add OAuth2 Client Credentials authentication for MCP servers
        # # the audience will be null if the JWT is intended for human users
        # if payload.get("aud") is None:
        token_data = TokenData(username=username)
        user = await users_service.get_user(session, username=token_data.username)
        if user is None:
            print(
                f"Couldn't find a user with the username '{token_data.username}'.")
            raise credentials_exception
        return user
    except InvalidTokenError:
        # TODO: uncomment and refactor this when you add OAuth2 Client Credentials authentication for MCP servers
    #     print("Couldn't verify the JWT is intended for a user. Attempting to verify for MCP server...")
    #     pass

    # try:
    #     payload = jwt.decode(
    #         token,
    #         JWT_SECRET_KEY.get_secret_value(),
    #         algorithms=[JWT_ALGORITHM.get_secret_value()],
    #         audience=JWT_AUDIENCE.get_secret_value()
    #     )

    #     # verify that the MCP client ID was provided
    #     if MCP_CLIENT_ID is None:
    #         raise RuntimeError(
    #             "MCP_CLIENT_ID is required to retrieve a JWT for the MCP server.")

    #     # verify that the payload includes the correct MCP client ID and required scopes
    #     client_id: str = payload.get("sub")
    #     if client_id != MCP_CLIENT_ID.get_secret_value():
    #         print(
    #             "Couldn't find the correct client_id for the MCP server provided in the JWT!")
    #         raise credentials_exception
    #     required_scopes = MCP_REQUIRED_SCOPES.get_secret_value().split(" ")
    #     scopes = payload.get("scope")
    #     for required in required_scopes:
    #         assert required in scopes, f"The required scope '{required}' is missing from the payload's scopes ('{scopes}')."

    #     # retrieve the "service" user associated with the MCP server
    #     service_user = await users_service.get_user(session, username=client_id)
    #     if service_user is None:
    #         print(
    #             f"Couldn't find a user with the username '{client_id}'.")
    #         raise credentials_exception
    #     return service_user
    # except InvalidTokenError:
        print("Couldn't verify the JWT!")
        raise credentials_exception
