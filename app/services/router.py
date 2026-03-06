from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.voice import MultiVoiceResponse, ParsedIntent, ParsedMultiIntent, VoiceResponse
from app.services.calendar import handle_calendar_action
from app.services.slack import handle_slack_action
from app.services.todoist import handle_todoist_action


async def route_actions(
    multi_intent: ParsedMultiIntent, user: User, db: AsyncSession
) -> MultiVoiceResponse:
    results = []
    for intent in multi_intent.intents:
        result = await _route_single(intent, user, db)
        results.append(result)

    successes = sum(1 for r in results if r.status == "success")
    if successes == len(results):
        status = "success"
    elif successes > 0:
        status = "partial"
    else:
        status = "error"

    return MultiVoiceResponse(status=status, results=results)


async def _route_single(
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
