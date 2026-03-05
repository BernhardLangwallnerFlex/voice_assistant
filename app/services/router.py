from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.voice import ParsedIntent, VoiceResponse
from app.services.calendar import handle_calendar_action
from app.services.slack import handle_slack_action
from app.services.todoist import handle_todoist_action


async def route_action(
    intent: ParsedIntent, user: User, db: AsyncSession
) -> VoiceResponse:
    if intent.service == "calendar" and intent.calendar:
        return await handle_calendar_action(intent.calendar, user, db)
    elif intent.service == "todoist" and intent.todoist:
        return await handle_todoist_action(intent.todoist, user, db)
    elif intent.service == "slack" and intent.slack:
        return await handle_slack_action(intent.slack)
    else:
        return VoiceResponse(
            status="error",
            service=intent.service,
            message=f"Unknown or incomplete intent for service: {intent.service}",
        )
