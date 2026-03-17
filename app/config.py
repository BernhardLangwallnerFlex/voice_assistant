import json
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    openai_api_key: str
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str
    encryption_key: str  # Fernet key, base64-encoded
    slack_bot_token: str = ""
    slack_contacts: str = "[]"  # JSON array: [{"name": "John Doe", "email": "john@co.com"}]
    audio_max_size_bytes: int = 10 * 1024 * 1024  # 10 MB
    audio_allowed_extensions: str = ".m4a,.mp3,.wav,.aac,.mp4"

    model_config = {"env_file": ".env", "extra": "ignore"}

    def get_slack_contacts(self) -> list[dict[str, str]]:
        return json.loads(self.slack_contacts)


@lru_cache
def get_settings() -> Settings:
    return Settings()
