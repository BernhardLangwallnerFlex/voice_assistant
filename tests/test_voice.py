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
    )
    assert intent.service == "calendar"
    assert intent.calendar.title == "Team standup"
    assert intent.todoist is None


def test_parsed_intent_todoist():
    from app.schemas.voice import ParsedIntent, TodoistIntent

    intent = ParsedIntent(
        service="todoist",
        todoist=TodoistIntent(content="Buy groceries", due_string="tomorrow"),
    )
    assert intent.service == "todoist"
    assert intent.todoist.content == "Buy groceries"
    assert intent.calendar is None


def test_parsed_multi_intent():
    from app.schemas.voice import ParsedIntent, ParsedMultiIntent, SlackIntent, TodoistIntent

    multi = ParsedMultiIntent(
        intents=[
            ParsedIntent(
                service="slack",
                slack=SlackIntent(
                    recipient_name="Oscar",
                    recipient_email="oscar@example.com",
                    message="I will be late 5 minutes",
                ),
            ),
            ParsedIntent(
                service="todoist",
                todoist=TodoistIntent(
                    content="Follow up with Oscar",
                    due_string="the day after tomorrow",
                ),
            ),
        ],
        raw_text="Send a Slack message to Oscar saying I will be late 5 minutes and set a reminder for follow up the day after tomorrow",
    )
    assert len(multi.intents) == 2
    assert multi.intents[0].service == "slack"
    assert multi.intents[1].service == "todoist"


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


def test_parsed_intent_rejects_missing_service_field():
    """ParsedIntent should reject when service field is null."""
    from pydantic import ValidationError

    from app.schemas.voice import ParsedIntent

    with pytest.raises(ValidationError, match="calendar field is null"):
        ParsedIntent(service="calendar")


def test_parsed_intent_rejects_wrong_field_populated():
    """ParsedIntent should reject when a non-matching service field is populated."""
    from pydantic import ValidationError

    from app.schemas.voice import CalendarIntent, ParsedIntent, TodoistIntent

    with pytest.raises(ValidationError, match="todoist field is populated"):
        ParsedIntent(
            service="calendar",
            calendar=CalendarIntent(
                title="Meeting",
                start_datetime="2025-01-15T09:00:00",
                end_datetime="2025-01-15T10:00:00",
            ),
            todoist=TodoistIntent(content="Oops"),
        )


def test_parsed_intent_rejects_invalid_service():
    """ParsedIntent should reject unknown service values."""
    from pydantic import ValidationError

    from app.schemas.voice import ParsedIntent

    with pytest.raises(ValidationError):
        ParsedIntent(service="email")
