from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from crud import users as user_crud
from ..schemas import Token, User, UserCreate
from ..security import create_access_token, get_current_user

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.post(
    "/",
    response_model=User,
    status_code=status.HTTP_201_CREATED
)
def register_user(
    user: UserCreate
) -> User:
    """
    Creates and returns a new user. This new user will be saved into the internal database.

    Throws a 400 if there is already a user with the same username in the database.

    Keyword arguments:

    user -- a `User` object with a username, password, email (optional), and full name (optional)
    """
    db_user = user_crud.get_user(username=user.username)
    if db_user:
        raise HTTPException(
            status_code=400, detail="A user with this username already registered.")
    return user_crud.create_user(user=user)


@router.post(
    "/token",
    response_model=Token
)
async def get_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Takes in the `username` and `password` from the OAuth2 form data. Logs the user in and returns an access token (JWT).

    Throws a 401 if the user provides an incorrect username or password.

    Keyword arguments:

    form_data -- a form that takes the `username` and `password` as inputs
    """
    user = user_crud.authenticate_user(form_data.username, form_data.password)
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
    response_model=User
)
async def read_users_me(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Returns the current authenticated user's details.

    Keyword arguments:

    current_user -- a `User` object with the current user's credentials
    """
    return current_user
