import io
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost/callback")
    monkeypatch.setenv("ENCRYPTION_KEY", key)

    from app.config import get_settings

    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


def test_voice_command_response_success():
    from app.schemas.voice_command import (
        ExecutionSummary,
        IntentSummary,
        LatencyBreakdown,
        VoiceCommandResponse,
    )

    resp = VoiceCommandResponse(
        ok=True,
        request_id="abc-123",
        mode="execute",
        transcript="remind me tomorrow to buy milk",
        normalized_text="remind me tomorrow to buy milk",
        intent=IntentSummary(service="todoist", action="create_task"),
        execution=ExecutionSummary(status="succeeded", provider="todoist"),
        result_text="Created task: buy milk",
        latency_ms=LatencyBreakdown(
            total=2000,
            upload_parse=50,
            transcription=1000,
            intent_parse=500,
            execution=400,
        ),
    )
    assert resp.ok is True
    assert resp.request_id == "abc-123"
    assert resp.intent.service == "todoist"
    assert resp.execution.status == "succeeded"
    assert resp.error is None


def test_voice_command_response_error():
    from app.schemas.voice_command import (
        ErrorPayload,
        LatencyBreakdown,
        VoiceCommandResponse,
    )

    resp = VoiceCommandResponse(
        ok=False,
        request_id="err-456",
        mode="execute",
        error=ErrorPayload(
            code="TRANSCRIPTION_FAILED",
            message="Could not transcribe",
            retryable=True,
        ),
        result_text="I couldn't understand the recording.",
        latency_ms=LatencyBreakdown(total=500),
    )
    assert resp.ok is False
    assert resp.error.code == "TRANSCRIPTION_FAILED"
    assert resp.error.retryable is True
    assert resp.transcript is None


def test_latency_breakdown_optional_fields():
    from app.schemas.voice_command import LatencyBreakdown

    lb = LatencyBreakdown(total=100)
    assert lb.total == 100
    assert lb.transcription is None
    assert lb.execution is None


# ---------------------------------------------------------------------------
# Transcription service tests
# ---------------------------------------------------------------------------


def test_locale_to_language():
    from app.services.transcription import _locale_to_language

    assert _locale_to_language("de-AT") == "de"
    assert _locale_to_language("en-US") == "en"
    assert _locale_to_language("fr") == "fr"
    assert _locale_to_language(None) is None
    assert _locale_to_language("") is None


@pytest.mark.asyncio
async def test_transcribe_audio_success(tmp_path):
    from app.services.transcription import TranscriptionResult, transcribe_audio

    audio_file = tmp_path / "test.m4a"
    audio_file.write_bytes(b"fake audio content")

    mock_response = MagicMock()
    mock_response.text = "  hello world  "

    mock_client = AsyncMock()
    mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)

    with patch("app.services.transcription.AsyncOpenAI", return_value=mock_client):
        result = await transcribe_audio(audio_file, locale="en-US")

    assert result.text == "hello world"
    assert result.language == "en"
    mock_client.audio.transcriptions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_transcribe_audio_failure(tmp_path):
    from app.services.transcription import TranscriptionError, transcribe_audio

    audio_file = tmp_path / "test.m4a"
    audio_file.write_bytes(b"fake audio")

    mock_client = AsyncMock()
    mock_client.audio.transcriptions.create = AsyncMock(
        side_effect=Exception("API error")
    )

    with patch("app.services.transcription.AsyncOpenAI", return_value=mock_client):
        with pytest.raises(TranscriptionError, match="Transcription failed"):
            await transcribe_audio(audio_file)


# ---------------------------------------------------------------------------
# Voice command service tests
# ---------------------------------------------------------------------------


def _make_upload_file(content: bytes = b"fake audio", filename: str = "test.m4a"):
    """Create a mock UploadFile."""
    upload = AsyncMock()
    upload.filename = filename
    upload.content_type = "audio/mp4"
    upload.read = AsyncMock(return_value=content)
    return upload


@pytest.mark.asyncio
async def test_handle_rejects_unsupported_extension():
    from app.services.voice_command import VoiceCommandService

    service = VoiceCommandService()
    audio = _make_upload_file(filename="test.txt")
    db = AsyncMock()
    user = MagicMock()
    user.timezone = "UTC"

    resp = await service.handle(
        user=user, audio=audio, db=db, request_id="req-1"
    )
    assert resp.ok is False
    assert resp.error.code == "UNSUPPORTED_AUDIO_TYPE"


@pytest.mark.asyncio
async def test_handle_rejects_empty_audio():
    from app.services.voice_command import VoiceCommandService

    service = VoiceCommandService()
    audio = _make_upload_file(content=b"", filename="test.m4a")
    db = AsyncMock()
    user = MagicMock()
    user.timezone = "UTC"

    resp = await service.handle(
        user=user, audio=audio, db=db, request_id="req-2"
    )
    assert resp.ok is False
    assert resp.error.code == "EMPTY_AUDIO"


@pytest.mark.asyncio
async def test_handle_rejects_oversized_audio(monkeypatch):
    monkeypatch.setenv("AUDIO_MAX_SIZE_BYTES", "100")
    from app.config import get_settings

    get_settings.cache_clear()

    from app.services.voice_command import VoiceCommandService

    service = VoiceCommandService()
    audio = _make_upload_file(content=b"x" * 200, filename="test.m4a")
    db = AsyncMock()
    user = MagicMock()
    user.timezone = "UTC"

    resp = await service.handle(
        user=user, audio=audio, db=db, request_id="req-3"
    )
    assert resp.ok is False
    assert resp.error.code == "PAYLOAD_TOO_LARGE"


@pytest.mark.asyncio
async def test_handle_empty_transcript():
    from app.services.transcription import TranscriptionResult
    from app.services.voice_command import VoiceCommandService

    service = VoiceCommandService()
    audio = _make_upload_file()
    db = AsyncMock()
    user = MagicMock()
    user.timezone = "UTC"

    with patch(
        "app.services.voice_command.transcribe_audio",
        new_callable=AsyncMock,
        return_value=TranscriptionResult(text=""),
    ):
        resp = await service.handle(
            user=user, audio=audio, db=db, request_id="req-4"
        )

    assert resp.ok is False
    assert resp.error.code == "EMPTY_TRANSCRIPT"


@pytest.mark.asyncio
async def test_handle_no_intent_detected():
    from app.schemas.voice import ParsedMultiIntent
    from app.services.transcription import TranscriptionResult
    from app.services.voice_command import VoiceCommandService

    service = VoiceCommandService()
    audio = _make_upload_file()
    db = AsyncMock()
    user = MagicMock()
    user.timezone = "UTC"

    with patch(
        "app.services.voice_command.transcribe_audio",
        new_callable=AsyncMock,
        return_value=TranscriptionResult(text="hello there"),
    ), patch(
        "app.services.voice_command.parse_voice_command",
        new_callable=AsyncMock,
        return_value=ParsedMultiIntent(intents=[], raw_text="hello there"),
    ):
        resp = await service.handle(
            user=user, audio=audio, db=db, request_id="req-5"
        )

    assert resp.ok is True
    assert resp.transcript == "hello there"
    assert "No actionable intent" in resp.result_text


@pytest.mark.asyncio
async def test_handle_dry_run_skips_execution():
    from app.schemas.voice import ParsedIntent, ParsedMultiIntent, TodoistIntent
    from app.services.transcription import TranscriptionResult
    from app.services.voice_command import VoiceCommandService

    service = VoiceCommandService()
    audio = _make_upload_file()
    db = AsyncMock()
    user = MagicMock()
    user.timezone = "UTC"

    multi = ParsedMultiIntent(
        intents=[
            ParsedIntent(
                service="todoist",
                todoist=TodoistIntent(content="Buy milk"),
            )
        ],
        raw_text="remind me to buy milk",
    )

    with patch(
        "app.services.voice_command.transcribe_audio",
        new_callable=AsyncMock,
        return_value=TranscriptionResult(text="remind me to buy milk"),
    ), patch(
        "app.services.voice_command.parse_voice_command",
        new_callable=AsyncMock,
        return_value=multi,
    ), patch(
        "app.services.voice_command.route_actions",
        new_callable=AsyncMock,
    ) as mock_route:
        resp = await service.handle(
            user=user, audio=audio, db=db, request_id="req-6", mode="dry_run"
        )

    assert resp.ok is True
    assert resp.mode == "dry_run"
    assert resp.execution.status == "previewed"
    assert resp.execution.dry_run is True
    mock_route.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_execute_success():
    from app.schemas.voice import (
        MultiVoiceResponse,
        ParsedIntent,
        ParsedMultiIntent,
        TodoistIntent,
        VoiceResponse,
    )
    from app.services.transcription import TranscriptionResult
    from app.services.voice_command import VoiceCommandService

    service = VoiceCommandService()
    audio = _make_upload_file()
    db = AsyncMock()
    user = MagicMock()
    user.timezone = "UTC"

    multi = ParsedMultiIntent(
        intents=[
            ParsedIntent(
                service="todoist",
                todoist=TodoistIntent(content="Buy milk", due_string="tomorrow"),
            )
        ],
        raw_text="remind me to buy milk tomorrow",
    )

    exec_response = MultiVoiceResponse(
        status="success",
        results=[
            VoiceResponse(
                status="success",
                service="todoist",
                message="Task created: Buy milk",
                details={"task_id": "t-123"},
            )
        ],
    )

    with patch(
        "app.services.voice_command.transcribe_audio",
        new_callable=AsyncMock,
        return_value=TranscriptionResult(text="remind me to buy milk tomorrow"),
    ), patch(
        "app.services.voice_command.parse_voice_command",
        new_callable=AsyncMock,
        return_value=multi,
    ), patch(
        "app.services.voice_command.route_actions",
        new_callable=AsyncMock,
        return_value=exec_response,
    ):
        resp = await service.handle(
            user=user, audio=audio, db=db, request_id="req-7"
        )

    assert resp.ok is True
    assert resp.mode == "execute"
    assert resp.transcript == "remind me to buy milk tomorrow"
    assert resp.intent.service == "todoist"
    assert resp.intent.action == "create_task"
    assert resp.execution.status == "succeeded"
    assert resp.execution.provider_reference == "t-123"
    assert "Task created" in resp.result_text
    assert resp.latency_ms.total >= 0


@pytest.mark.asyncio
async def test_handle_transcription_failure():
    from app.services.transcription import TranscriptionError
    from app.services.voice_command import VoiceCommandService

    service = VoiceCommandService()
    audio = _make_upload_file()
    db = AsyncMock()
    user = MagicMock()
    user.timezone = "UTC"

    with patch(
        "app.services.voice_command.transcribe_audio",
        new_callable=AsyncMock,
        side_effect=TranscriptionError("API timeout"),
    ):
        resp = await service.handle(
            user=user, audio=audio, db=db, request_id="req-8"
        )

    assert resp.ok is False
    assert resp.error.code == "TRANSCRIPTION_FAILED"
    assert resp.error.retryable is True
