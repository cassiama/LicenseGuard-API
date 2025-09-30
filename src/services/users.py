from typing import Optional
from sqlmodel.ext.asyncio.session import AsyncSession
from crud.users import get_user_by_username, save_user
from srv.schemas import UserPublic, UserCreate, User
from srv.security import verify_pwd, get_hashed_pwd


async def get_user(session: AsyncSession, username: str) -> Optional[UserPublic]:
    """
    Business logic to retrieve a user. Will return a valid `UserPublic` if provided a valid `username`. Otherwise, it will return `None`.
    """
    # TODO: implement more complex business logic when the app requires it
    user = await get_user_by_username(session, username)
    if user:
        return UserPublic.model_validate(user, from_attributes=True)
    return None


async def authenticate_user(session: AsyncSession, username: str, password: str) -> Optional[UserPublic]:
    """
    Given a `username` and `password` associated with a valid user, this will return a `UserPublic`. Otherwise, it will return `None`.
    """
    # verify the password of the user (requires the User)
    user: Optional[User] = await get_user_by_username(session, username)
    if not user:
        return None
    if not verify_pwd(password, user.hashed_password):
        return None

    # once proven successful, return the user
    return UserPublic.model_validate(user, from_attributes=True)


async def create_user(session: AsyncSession, user: UserCreate) -> UserPublic:
    """
    Creates and returns a new `UserPublic`. Saves the new user in the database. Does not return the password.
    """
    # ensure that the user is valid
    if len(user.username) < 4 or len(user.username) > 100:
        raise ValueError("Username must be between 4 and 100 characters.")
    if len(user.password) < 4:
        raise ValueError("Password must be at least 4 characters.")

    # also ensure that there isn't an existing user with the same username
    existing_user = await get_user_by_username(session, user.username)
    if existing_user:
        raise ValueError("A user with this username is already registered.")

    hashed_pwd = get_hashed_pwd(user.password)
    user_in_db = User(
        **user.model_dump(),
        hashed_password=hashed_pwd
    )

    # use the database layer to save the user
    await save_user(session, user_in_db)

    # this should return a valid UserPublic object WITHOUT the password
    return UserPublic.model_validate(user_in_db, from_attributes=True)
