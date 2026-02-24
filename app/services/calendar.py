import json

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.integration import Integration
from app.models.user import User
from app.schemas.voice import CalendarIntent, VoiceResponse
from app.utils.crypto import decrypt


def _build_calendar_service(refresh_token: str):
    settings = get_settings()
    credentials = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
    )
    return build("calendar", "v3", credentials=credentials)


async def handle_calendar_action(
    intent: CalendarIntent, user: User, db: AsyncSession
) -> VoiceResponse:
    result = await db.execute(
        select(Integration).where(
            Integration.user_id == user.id,
            Integration.service == "google",
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        return VoiceResponse(
            status="error",
            service="calendar",
            message="Google not connected. Visit /auth/google/start to connect.",
        )

    creds_data = json.loads(decrypt(integration.encrypted_credentials))
    service = _build_calendar_service(creds_data["refresh_token"])

    event_body: dict = {
        "summary": intent.title,
        "start": {
            "dateTime": intent.start_datetime.isoformat(),
            "timeZone": user.timezone,
        },
        "end": {
            "dateTime": intent.end_datetime.isoformat(),
            "timeZone": user.timezone,
        },
    }
    if intent.location:
        event_body["location"] = intent.location
    if intent.description:
        event_body["description"] = intent.description
    if intent.invitees:
        event_body["attendees"] = [{"email": e} for e in intent.invitees]

    created = service.events().insert(calendarId="primary", body=event_body).execute()

    return VoiceResponse(
        status="success",
        service="calendar",
        message=f"Event '{intent.title}' created",
        details={"event_id": created.get("id"), "link": created.get("htmlLink")},
    )
