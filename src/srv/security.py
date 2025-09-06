import jwt
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from pydantic import SecretStr
from core.config import Settings
from srv.schemas import TokenData, User


# import the JWT config variables
settings = Settings()

# setup password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# setup OAuth2 scheme; points to the login route
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
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload.update({"exp": expire})
    try:
        # if the JWT_SECRET_KEY was imported from the .env file, then we need to convert it to a string
        # otherwise, it might be an automatically generated value (see core/config.py)
        is_secret_str = type(settings.jwt_secret_key) is SecretStr
        is_str = type(settings.jwt_secret_key) is str
        if is_secret_str or is_str:
            access_token = jwt.encode(
                payload,
                str(settings.jwt_secret_key) if is_secret_str else settings.jwt_secret_key,
                algorithm=settings.jwt_algorithm
            )
            return access_token
        
        else:
            raise TypeError("Expected a string (or SecretStr) value")
    except TypeError as e:
        raise e

# dependency for retrieving the current authenticated user


def get_current_user(
        token: Annotated[str, Depends(oauth2)]
) -> User:
    # TODO: after you confirm everything is working, move this import to the top of the file and see what happens/breaks
    # import crud here to avoid a circular dependency
    from crud import users as users_crud

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate user credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # if the JWT_SECRET_KEY was imported from the .env file, then we need to convert it to a string
        # otherwise, it might be an automatically generated value (see core/config.py)
        is_secret_str = type(settings.jwt_secret_key) is SecretStr
        is_str = type(settings.jwt_secret_key) is str
        if is_secret_str or is_str:
            payload = jwt.decode(
                token,
                str(settings.jwt_secret_key) if is_secret_str else settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
            token_data = TokenData(username=username)
        else:
            raise TypeError("Expected a string (or SecretStr) value")
    except TypeError as e:
        raise e
    except InvalidTokenError:
        raise credentials_exception

    user = users_crud.get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user
