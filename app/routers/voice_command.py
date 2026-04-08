import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.command_log import CommandLog
from app.models.user import User
from app.schemas.voice_command import VoiceCommandResponse
from app.services.voice_command import VoiceCommandService
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/voice", tags=["voice-commands"])


@router.post("/commands", response_model=VoiceCommandResponse)
async def create_voice_command(
    audio: UploadFile = File(...),
    client: str | None = Form(default=None),
    device_id: str | None = Form(default=None),
    shortcut_version: str | None = Form(default=None),
    timezone: str | None = Form(default=None),
    locale: str | None = Form(default=None),
    submitted_at: datetime | None = Form(default=None),
    request_id: str | None = Form(default=None),
    mode: str = Form(default="execute"),
    return_debug: bool = Form(default=False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VoiceCommandResponse:
    """Accept a short uploaded audio recording, transcribe, parse intent,
    optionally execute, and return a compact JSON response."""
    if not request_id:
        request_id = str(uuid.uuid4())

    service = VoiceCommandService()
    response = await service.handle(
        user=user,
        audio=audio,
        request_id=request_id,
        mode=mode,
        timezone=timezone,
        locale=locale,
        db=db,
    )

    if response.transcript:
        db.add(CommandLog(user_id=user.id, endpoint="voice_command", transcription=response.transcript))
        await db.commit()

    logger.info(
        "voice_command completed: request_id=%s user_id=%s mode=%s ok=%s "
        "intent_service=%s latency_total_ms=%d",
        response.request_id,
        user.id,
        response.mode,
        response.ok,
        response.intent.service if response.intent else None,
        response.latency_ms.total,
    )

    return response
