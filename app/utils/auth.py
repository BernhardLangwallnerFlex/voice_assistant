from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.user import User

api_key_header = APIKeyHeader(name="X-API-Key")


async def get_current_user(
    api_key: str = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> User:
    result = await db.execute(select(User).where(User.api_key == api_key))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user
