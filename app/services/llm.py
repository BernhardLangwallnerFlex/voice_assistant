from datetime import datetime, timezone

from openai import AsyncOpenAI

from app.config import get_settings
from app.schemas.voice import ParsedIntent

SYSTEM_PROMPT = """\
You are a voice command parser. Given a natural language command, extract structured intent as JSON.

Determine which service the user wants:
- "calendar" for scheduling events, meetings, appointments
- "todoist" for tasks, to-dos, reminders

Current date and time: {now}
User's timezone: {timezone}

Return JSON matching this exact schema:
{{
  "service": "calendar" or "todoist",
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
  "raw_text": "the original voice command"
}}

Only populate the object for the detected service; set the other to null.
For calendar events without an explicit end time, default to 1 hour after start.
"""


async def parse_voice_command(text: str, user_timezone: str) -> ParsedIntent:
    client = AsyncOpenAI(api_key=get_settings().openai_api_key)

    now = datetime.now(timezone.utc).isoformat()

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(now=now, timezone=user_timezone),
            },
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
    )

    raw_json = response.choices[0].message.content
    return ParsedIntent.model_validate_json(raw_json)
