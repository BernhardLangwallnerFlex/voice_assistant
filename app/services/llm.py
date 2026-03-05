from datetime import datetime, timezone

from openai import AsyncOpenAI

from app.config import get_settings
from app.schemas.voice import ParsedIntent

SYSTEM_PROMPT = """\
You are a voice command parser. Given a natural language command, extract structured intent as JSON.

Determine which service the user wants:
- "calendar" for scheduling events, meetings, appointments
- "todoist" for tasks, to-dos, reminders
- "slack" for sending messages to people via Slack

Current date and time: {now}
User's timezone: {timezone}

Allowed Slack contacts (only these people can be messaged):
{slack_contacts}

Return JSON matching this exact schema:
{{
  "service": "calendar" or "todoist" or "slack",
  "calendar": {{
    "action": "create_event",
    "title": "string",
    "start_datetime": "ISO 8601 datetime",
    "end_datetime": "ISO 8601 datetime",
    "location": "string or null",
    "description": "string or null",
    "invitees": ["email1", "email2"] or null
  }} or null,
  "todoist": {{
    "action": "create_task",
    "content": "task title string",
    "description": "additional details or null",
    "due_string": "natural language date or null",
    "priority": "integer: 4=urgent(p1), 3=high(p2), 2=medium(p3), 1=normal(p4, default). NOTE: higher number = higher priority",
    "project": "exact project name as spoken or null",
    "labels": ["label1", "label2"] or null
  }} or null,
  "slack": {{
    "action": "send_message",
    "recipient_name": "the person's full name from the contacts list",
    "recipient_email": "the person's email from the contacts list",
    "message": "the message to send"
  }} or null,
  "raw_text": "the original voice command"
}}

Only populate the object for the detected service; set the others to null.
For calendar events without an explicit end time, default to 1 hour after start.
For Slack messages, you MUST use the exact email from the allowed contacts list. Match the spoken name to the closest contact.
"""


async def parse_voice_command(text: str, user_timezone: str) -> ParsedIntent:
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    now = datetime.now(timezone.utc).isoformat()

    contacts = settings.get_slack_contacts()
    contacts_str = "\n".join(
        f"- {c['name']} ({c['email']})" for c in contacts
    ) if contacts else "No contacts configured."

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(
                    now=now, timezone=user_timezone, slack_contacts=contacts_str
                ),
            },
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
    )

    raw_json = response.choices[0].message.content
    return ParsedIntent.model_validate_json(raw_json)
