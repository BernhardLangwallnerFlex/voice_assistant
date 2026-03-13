import asyncio
import json
import logging
from datetime import datetime, timezone

from openai import AsyncOpenAI

from app.config import get_settings
from app.schemas.voice import (
    CalendarIntent,
    ParsedIntent,
    ParsedMultiIntent,
    SlackIntent,
    TodoistIntent,
)
from app.services.classifier import classify_intents
from app.services.prompts import CALENDAR_PROMPT, SLACK_PROMPT, TODOIST_PROMPT

logger = logging.getLogger(__name__)

_PROMPT_MAP = {
    "calendar": CALENDAR_PROMPT,
    "todoist": TODOIST_PROMPT,
    "slack": SLACK_PROMPT,
}

_MODEL_MAP = {
    "calendar": CalendarIntent,
    "todoist": TodoistIntent,
    "slack": SlackIntent,
}


async def parse_voice_command(text: str, user_timezone: str) -> ParsedMultiIntent:
    services = classify_intents(text)

    if not services:
        return ParsedMultiIntent(intents=[], raw_text=text)

    tasks = [_extract_intent(service, text, user_timezone) for service in services]
    results = await asyncio.gather(*tasks)

    intents = [r for r in results if r is not None]
    return ParsedMultiIntent(intents=intents, raw_text=text)


async def _extract_intent(
    service: str, text: str, user_timezone: str
) -> ParsedIntent | None:
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    now = datetime.now(timezone.utc).isoformat()

    prompt_template = _PROMPT_MAP[service]
    format_kwargs = {"now": now, "timezone": user_timezone}

    if service == "slack":
        contacts = settings.get_slack_contacts()
        format_kwargs["slack_contacts"] = (
            "\n".join(f"- {c['name']} ({c['email']})" for c in contacts)
            if contacts
            else "No contacts configured."
        )

    system_content = prompt_template.format(**format_kwargs)

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
        )

        raw_json = response.choices[0].message.content
        data = json.loads(raw_json)

        result = data.get("result")
        if result is None:
            return None

        model_class = _MODEL_MAP[service]
        parsed = model_class.model_validate(result)

        return ParsedIntent(service=service, **{service: parsed})

    except Exception:
        logger.exception("Failed to extract %s intent from: %s", service, text)
        return None
