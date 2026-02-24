"""Create a test user with a generated API key."""

import asyncio
import secrets

from sqlalchemy import select

from app.db import async_session
from app.models.user import User


async def create_user(timezone: str = "Europe/Vienna") -> None:
    api_key = secrets.token_hex(32)

    async with async_session() as session:
        # Check if any user exists already
        result = await session.execute(select(User))
        existing = result.scalars().first()
        if existing:
            print(f"User already exists: id={existing.id}, api_key={existing.api_key}")
            return

        user = User(api_key=api_key, timezone=timezone)
        session.add(user)
        await session.commit()
        await session.refresh(user)

        print(f"User created!")
        print(f"  id:       {user.id}")
        print(f"  api_key:  {user.api_key}")
        print(f"  timezone: {user.timezone}")
        print(f"\nUse this header for requests:")
        print(f'  X-API-Key: {user.api_key}')


if __name__ == "__main__":
    asyncio.run(create_user())
