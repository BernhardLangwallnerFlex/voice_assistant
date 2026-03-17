import logging
import os
import re
import tempfile
import time
import uuid
from pathlib import Path

from fastapi import UploadFile
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User
from app.schemas.voice_command import (
    ErrorPayload,
    ExecutionSummary,
    IntentSummary,
    LatencyBreakdown,
    VoiceCommandResponse,
)
from app.services.llm import parse_voice_command
from app.services.router import route_actions
from app.services.transcription import TranscriptionError, transcribe_audio

logger = logging.getLogger(__name__)


def _normalize_transcript(text: str) -> str:
    """Trim whitespace and collapse multiple spaces."""
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _ms_since(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


class AudioValidationError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class VoiceCommandService:
    async def handle(
        self,
        *,
        user: User,
        audio: UploadFile,
        request_id: str | None = None,
        mode: str = "execute",
        timezone: str | None = None,
        locale: str | None = None,
        db: AsyncSession,
    ) -> VoiceCommandResponse:
        request_id = request_id or str(uuid.uuid4())
        effective_mode = "dry_run" if mode == "dry_run" else "execute"
        effective_timezone = timezone or user.timezone or "UTC"

        total_start = time.monotonic()
        upload_parse_ms = None
        transcription_ms = None
        intent_parse_ms = None
        execution_ms = None

        tmp_path: Path | None = None

        try:
            # --- Validate & save to temp file ---
            step_start = time.monotonic()
            tmp_path = await self._validate_and_save(audio)
            upload_parse_ms = _ms_since(step_start)

            # --- Transcribe ---
            step_start = time.monotonic()
            transcription_result = await transcribe_audio(tmp_path, locale)
            transcription_ms = _ms_since(step_start)

            transcript = transcription_result.text
            if not transcript:
                return self._error_response(
                    request_id=request_id,
                    mode=effective_mode,
                    code="EMPTY_TRANSCRIPT",
                    message="The audio could not be transcribed clearly.",
                    result_text="I couldn't understand the recording. Please try again.",
                    retryable=True,
                    latency=LatencyBreakdown(
                        total=_ms_since(total_start),
                        upload_parse=upload_parse_ms,
                        transcription=transcription_ms,
                    ),
                )

            normalized = _normalize_transcript(transcript)

            # --- Parse intent ---
            step_start = time.monotonic()
            try:
                multi_intent = await parse_voice_command(
                    normalized, effective_timezone
                )
            except ValidationError:
                logger.error("LLM returned invalid JSON during voice command")
                return self._error_response(
                    request_id=request_id,
                    mode=effective_mode,
                    code="INTENT_PARSE_FAILED",
                    message="Could not parse the voice command.",
                    result_text="I understood the words but couldn't figure out the action. Please try rephrasing.",
                    retryable=True,
                    transcript=transcript,
                    normalized_text=normalized,
                    latency=LatencyBreakdown(
                        total=_ms_since(total_start),
                        upload_parse=upload_parse_ms,
                        transcription=transcription_ms,
                        intent_parse=_ms_since(step_start),
                    ),
                )
            intent_parse_ms = _ms_since(step_start)

            # No actionable intent
            if not multi_intent.intents:
                return VoiceCommandResponse(
                    ok=True,
                    request_id=request_id,
                    mode=effective_mode,
                    transcript=transcript,
                    normalized_text=normalized,
                    result_text="No actionable intent detected. Try keywords like 'remind me', 'schedule a meeting', or 'slack'.",
                    latency_ms=LatencyBreakdown(
                        total=_ms_since(total_start),
                        upload_parse=upload_parse_ms,
                        transcription=transcription_ms,
                        intent_parse=intent_parse_ms,
                    ),
                )

            # Build intent summary from first intent
            first_intent = multi_intent.intents[0]
            intent_data = getattr(first_intent, first_intent.service)
            intent_summary = IntentSummary(
                service=first_intent.service,
                action=getattr(intent_data, "action", None),
            )

            # --- Dry run: skip execution ---
            if effective_mode == "dry_run":
                return VoiceCommandResponse(
                    ok=True,
                    request_id=request_id,
                    mode="dry_run",
                    transcript=transcript,
                    normalized_text=normalized,
                    intent=intent_summary,
                    execution=ExecutionSummary(
                        status="previewed",
                        provider=first_intent.service,
                        dry_run=True,
                    ),
                    result_text=f"Dry run: detected {first_intent.service} intent ({intent_data.action}).",
                    latency_ms=LatencyBreakdown(
                        total=_ms_since(total_start),
                        upload_parse=upload_parse_ms,
                        transcription=transcription_ms,
                        intent_parse=intent_parse_ms,
                    ),
                )

            # --- Execute ---
            step_start = time.monotonic()
            multi_response = await route_actions(multi_intent, user, db)
            execution_ms = _ms_since(step_start)

            # Map MultiVoiceResponse → VoiceCommandResponse
            all_messages = [r.message for r in multi_response.results]
            result_text = " | ".join(all_messages)

            ok = multi_response.status in ("success", "partial")
            exec_status = {
                "success": "succeeded",
                "partial": "succeeded",
                "error": "failed",
            }.get(multi_response.status, "failed")

            # Extract provider reference from first result's details
            first_result = multi_response.results[0] if multi_response.results else None
            provider_ref = None
            if first_result and first_result.details:
                provider_ref = (
                    first_result.details.get("event_id")
                    or first_result.details.get("task_id")
                    or first_result.details.get("channel")
                )

            return VoiceCommandResponse(
                ok=ok,
                request_id=request_id,
                mode="execute",
                transcript=transcript,
                normalized_text=normalized,
                intent=intent_summary,
                execution=ExecutionSummary(
                    status=exec_status,
                    provider=first_intent.service,
                    provider_reference=str(provider_ref) if provider_ref else None,
                    dry_run=False,
                ),
                result_text=result_text,
                latency_ms=LatencyBreakdown(
                    total=_ms_since(total_start),
                    upload_parse=upload_parse_ms,
                    transcription=transcription_ms,
                    intent_parse=intent_parse_ms,
                    execution=execution_ms,
                ),
            )

        except AudioValidationError as e:
            return self._error_response(
                request_id=request_id,
                mode=effective_mode,
                code=e.code,
                message=e.message,
                result_text=e.message,
                retryable=False,
                latency=LatencyBreakdown(
                    total=_ms_since(total_start),
                    upload_parse=upload_parse_ms,
                ),
            )

        except TranscriptionError as e:
            return self._error_response(
                request_id=request_id,
                mode=effective_mode,
                code="TRANSCRIPTION_FAILED",
                message=str(e),
                result_text="I couldn't clearly understand the recording. Please try again.",
                retryable=True,
                latency=LatencyBreakdown(
                    total=_ms_since(total_start),
                    upload_parse=upload_parse_ms,
                    transcription=transcription_ms,
                ),
            )

        except Exception as e:
            logger.exception("Unexpected error in voice command handler")
            return self._error_response(
                request_id=request_id,
                mode=effective_mode,
                code="INTERNAL_ERROR",
                message="An unexpected error occurred.",
                result_text="Something went wrong. Please try again later.",
                retryable=True,
                latency=LatencyBreakdown(total=_ms_since(total_start)),
            )

        finally:
            if tmp_path and tmp_path.exists():
                try:
                    os.unlink(tmp_path)
                except OSError:
                    logger.warning("Failed to delete temp file: %s", tmp_path)

    async def _validate_and_save(self, audio: UploadFile) -> Path:
        """Validate the uploaded audio and save to a temp file."""
        settings = get_settings()
        allowed = settings.audio_allowed_extensions.split(",")

        # Check filename extension
        filename = audio.filename or ""
        ext = Path(filename).suffix.lower()
        if not ext or ext not in allowed:
            raise AudioValidationError(
                code="UNSUPPORTED_AUDIO_TYPE",
                message=f"Unsupported audio format. Accepted: {', '.join(allowed)}",
                status_code=415,
            )

        # Read content and check size
        content = await audio.read()
        if len(content) == 0:
            raise AudioValidationError(
                code="EMPTY_AUDIO",
                message="The uploaded audio file is empty.",
                status_code=400,
            )
        if len(content) > settings.audio_max_size_bytes:
            max_mb = settings.audio_max_size_bytes / (1024 * 1024)
            raise AudioValidationError(
                code="PAYLOAD_TOO_LARGE",
                message=f"Audio file exceeds the {max_mb:.0f} MB limit.",
                status_code=413,
            )

        # Save to temp file
        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        try:
            tmp.write(content)
            tmp.flush()
        finally:
            tmp.close()

        return Path(tmp.name)

    @staticmethod
    def _error_response(
        *,
        request_id: str,
        mode: str,
        code: str,
        message: str,
        result_text: str,
        retryable: bool = False,
        transcript: str | None = None,
        normalized_text: str | None = None,
        latency: LatencyBreakdown,
    ) -> VoiceCommandResponse:
        return VoiceCommandResponse(
            ok=False,
            request_id=request_id,
            mode=mode,
            transcript=transcript,
            normalized_text=normalized_text,
            error=ErrorPayload(code=code, message=message, retryable=retryable),
            result_text=result_text,
            latency_ms=latency,
        )
