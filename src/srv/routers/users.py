from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from db.session import get_db
from services.users import get_user, create_user, authenticate_user
from ..schemas import Token, UserPublic, UserCreate
from ..security import create_access_token, get_current_user

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.post(
    "/",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED
)
async def register_user(
    user_in: UserCreate,
    session: AsyncSession = Depends(get_db)
) -> UserPublic:
    """
    Creates and returns a new user. This new user will be saved into the internal database.

    Throws a 400 if there is already a user with the same username in the database.

    Throws a 422 if:
     - the username is less than 4 or greater than 100 characters.
     - the password is less than 4 characters.

    Keyword arguments:

    user_in -- a `UserCreate` object with a username, password, email (optional), and full name (optional)
    """
    if len(user_in.username) < 4 or len(user_in.username) > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Username must be between 4 and 100 characters."
        )
    if len(user_in.password) < 4:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Password must be at least 4 characters."
        )

    db_user = get_user(session, username=user_in.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="A user with this username is already registered.")
    user = await create_user(session, user=user_in)
    return user


@router.post(
    "/token",
    response_model=Token
)
async def get_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db)
):
    """
    Takes in the `username` and `password` from the OAuth2 form data. Logs the user in and returns an access token (JWT).

    Throws a 401 if the user provides an incorrect username or password.

    Keyword arguments:

    form_data -- a form that takes the `username` and `password` as inputs
    """
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        {"sub": user.username}, expires_delta=None)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get(
    "/me",
    response_model=UserPublic
)
async def read_users_me(
    current_user: UserPublic = Depends(get_current_user)
) -> UserPublic:
    """
    Returns the current authenticated user's details.

    Keyword arguments:

    current_user -- a `UserPublic` object with the current user's credentials
    """
    return current_user
