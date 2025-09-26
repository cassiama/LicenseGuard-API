from typing import Optional
from db.db import get_user_by_username, save_user
from srv.schemas import UserPublic, UserCreate, User
from srv.security import verify_pwd, get_hashed_pwd


def get_user(username: str) -> Optional[UserPublic]:
    """
    Business logic to retrieve a user. Will return a valid `UserPublic` if provided a valid `username`. Otherwise, it will return `None`.
    """
    # TODO: implement more complex business logic when the app requires it
    user = get_user_by_username(username)
    if user:
        return UserPublic.model_validate(user, from_attributes=True)
    return None


def authenticate_user(username: str, password: str) -> Optional[UserPublic]:
    """
    Given a `username` and `password` associated with a valid user, this will return a `UserPublic`. Otherwise, it will return `None`.
    """
    # get the base user from the db (we literally only do this to return the UserPublic at the end)
    user = get_user(username)
    if not user:
        return None

    # verify the password of the user (requires the User)
    user_in_db: Optional[User] = get_user_by_username(username)
    if not user_in_db:
        return None
    if not verify_pwd(password, user_in_db.hashed_password):
        return None

    # once proven successful, return the user
    return user


def create_user(user: UserCreate) -> UserPublic:
    """
    Creates and returns a new `UserPublic`. Saves the new user in the database. Does not return the password.
    """
    hashed_pwd = get_hashed_pwd(user.password)
    user_in_db = User(
        **user.model_dump(),
        hashed_password=hashed_pwd
    )

    # use the database layer to save the user
    save_user(user_in_db)

    # this should return a valid UserPublic object WITHOUT the password
    return UserPublic.model_validate(user_in_db, from_attributes=True)
