from datetime import datetime, timezone

from openai import AsyncOpenAI

from app.config import get_settings
from app.schemas.voice import ParsedMultiIntent

from app.services.prompts import SYSTEM_PROMPT

async def parse_voice_command(text: str, user_timezone: str) -> ParsedMultiIntent:
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
    return ParsedMultiIntent.model_validate_json(raw_json)
