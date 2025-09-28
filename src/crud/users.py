from typing import Optional
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from srv.schemas import User


async def get_user_by_username(session: AsyncSession, username: str) -> Optional[User]:
    """
    Retrieves a single user from the database by their username.
    """
    if len(username) < 4 or len(username) > 100:
        raise ValueError("Username must be between 4 and 100 characters.")
    
    result = await session.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def save_user(session: AsyncSession, user: User) -> User:
    """
    Saves a user to the database.
    """
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
