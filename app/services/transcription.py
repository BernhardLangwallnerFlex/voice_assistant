import logging
from pathlib import Path

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger(__name__)

# Domain-specific terms to bias transcription toward correct spellings.
# The transcription model uses this as a conditioning hint for ambiguous audio.
TRANSCRIPTION_PROMPT = (
    "Flex, Flex's, Omikron, Evex, Nitrado, 3C, Todoist, Mem, Simovative"
)


class TranscriptionResult(BaseModel):
    text: str
    duration_seconds: float | None = None
    language: str | None = None


class TranscriptionError(Exception):
    pass


def _locale_to_language(locale: str | None) -> str | None:
    """Extract ISO 639-1 language code from a locale string like 'de-AT'."""
    if not locale:
        return None
    return locale.split("-")[0].lower() or None


async def transcribe_audio(
    file_path: Path, locale: str | None = None
) -> TranscriptionResult:
    """Transcribe an audio file using OpenAI Whisper."""
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    language = _locale_to_language(locale)

    try:
        with open(file_path, "rb") as audio_file:
            response = await client.audio.transcriptions.create(
                model="gpt-4o-transcribe",
                file=audio_file,
                prompt=TRANSCRIPTION_PROMPT,
                **({"language": language} if language else {}),
            )

        text = response.text.strip()
        logger.info(
            "Transcription complete: %d chars, language_hint=%s",
            len(text),
            language,
        )
        return TranscriptionResult(text=text, language=language)

    except Exception as e:
        logger.exception("Transcription failed for %s", file_path)
        raise TranscriptionError(f"Transcription failed: {e}") from e
