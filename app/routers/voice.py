import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.user import User
from app.schemas.voice import VoiceRequest, VoiceResponse
from app.services.llm import parse_voice_command
from app.services.router import route_action
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/voice", response_model=VoiceResponse)
async def handle_voice(
    request: VoiceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        intent = await parse_voice_command(request.text, user.timezone)
    except ValidationError as e:
        logger.error("LLM returned invalid JSON: %s", e)
        raise HTTPException(
            status_code=422,
            detail="Could not parse voice command. Please try rephrasing.",
        )

    return await route_action(intent, user, db)
