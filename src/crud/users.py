from typing import Optional
from db.db import get_user_by_username, save_user
from srv.schemas import User, UserCreate, UserInDB
from srv.security import verify_pwd, get_hashed_pwd


def get_user(username: str) -> Optional[User]:
    """
    Business logic to retrieve a user. Will return a valid `User` if provided a valid `username`. Otherwise, it will return `None`.
    """
    # TODO: implement more complex business logic when the app requires it
    user = get_user_by_username(username)
    if user:
        return User.model_validate(user, from_attributes=True)
    return None

def authenticate_user(username: str, password: str) -> Optional[User]:
    """
    Given a `username` and `password` associated with a valid user, this will return a `User`. Otherwise, it will return `None`.
    """
    # get the base user from the db (we literally only do this to return the User at the end)
    user = get_user(username)
    if not user:
        return None
    
    # verify the password of the user (requires the UserInDB)
    user_in_db: Optional[UserInDB] = get_user_by_username(username)
    if not user_in_db:
        return None
    if not verify_pwd(password, user_in_db.hashed_password):
        return None
    
    # once proven successful, return the user
    return user

def create_user(user: UserCreate) -> User:
    """
    Creates and returns a new `User`. Saves the new user in the database. Does not return the password.
    """
    hashed_pwd = get_hashed_pwd(user.password)
    user_in_db = UserInDB(
        **user.model_dump(),
        hashed_password=hashed_pwd
    )
    
    # use the database layer to save the user
    save_user(user_in_db)

    # this should return a valid User object WITHOUT the password
    return User.model_validate(user_in_db, from_attributes=True)