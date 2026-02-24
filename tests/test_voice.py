from unittest.mock import AsyncMock, patch

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


def test_parsed_intent_calendar():
    from app.schemas.voice import CalendarIntent, ParsedIntent

    intent = ParsedIntent(
        service="calendar",
        calendar=CalendarIntent(
            title="Team standup",
            start_datetime="2025-01-15T09:00:00",
            end_datetime="2025-01-15T10:00:00",
        ),
        raw_text="Schedule team standup tomorrow at 9am",
    )
    assert intent.service == "calendar"
    assert intent.calendar.title == "Team standup"
    assert intent.todoist is None


def test_parsed_intent_todoist():
    from app.schemas.voice import ParsedIntent, TodoistIntent

    intent = ParsedIntent(
        service="todoist",
        todoist=TodoistIntent(content="Buy groceries", due_string="tomorrow"),
        raw_text="Remind me to buy groceries tomorrow",
    )
    assert intent.service == "todoist"
    assert intent.todoist.content == "Buy groceries"
    assert intent.calendar is None


def test_voice_response_model():
    from app.schemas.voice import VoiceResponse

    resp = VoiceResponse(
        status="success",
        service="calendar",
        message="Event created",
        details={"event_id": "123"},
    )
    assert resp.status == "success"
    assert resp.details["event_id"] == "123"
