import asyncio

from app.config import get_settings
from app.schemas.voice import SlackIntent, VoiceResponse
from app.services.slack_messenger import SlackMessenger


async def handle_slack_action(intent: SlackIntent) -> VoiceResponse:
    settings = get_settings()

    token = settings.slack_user_token if intent.as_user else settings.slack_bot_token
    token_label = "Slack user token" if intent.as_user else "Slack bot token"

    if not token:
        return VoiceResponse(
            status="error",
            service="slack",
            message=f"{token_label} not configured.",
        )

    # Validate recipient is in the whitelist
    contacts = settings.get_slack_contacts()
    allowed_emails = {c["email"] for c in contacts}
    if intent.recipient_email not in allowed_emails:
        return VoiceResponse(
            status="error",
            service="slack",
            message=f"Recipient '{intent.recipient_name}' is not in the allowed contacts list.",
        )

    messenger = SlackMessenger(token=token)

    try:
        await asyncio.to_thread(
            messenger.send_dm, intent.recipient_email, intent.message
        )
    except Exception as e:
        return VoiceResponse(
            status="error",
            service="slack",
            message=f"Failed to send Slack message: {e}",
        )

    return VoiceResponse(
        status="success",
        service="slack",
        message=f"Message sent to {intent.recipient_name}.",
        details={
            "recipient": intent.recipient_name,
            "recipient_email": intent.recipient_email,
        },
    )
