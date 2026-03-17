"""Quick script to test the voice command audio upload flow."""

import asyncio
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

# BASE_URL = "http://127.0.0.1:8000"
BASE_URL = "https://voice-assistant-3tzm.onrender.com/"
API_KEY = os.environ.get("API_KEY", "YOUR_API_KEY")
print(f"API_KEY: {API_KEY}")

AUDIO_FILE = "audio1.m4a"


def print_response(resp: httpx.Response):
    print(f"Status: {resp.status_code}")
    try:
        import json
        print(json.dumps(resp.json(), indent=2))
    except Exception:
        print(resp.text)


async def main():
    print(f"Using API_KEY: {API_KEY[:8]}...")
    print(f"Audio file: {AUDIO_FILE}\n")

    if not os.path.exists(AUDIO_FILE):
        print(f"ERROR: '{AUDIO_FILE}' not found. Place an audio file in the project root.")
        return

    async with httpx.AsyncClient(
        base_url=BASE_URL, headers={"X-API-Key": API_KEY}, timeout=60
    ) as client:
        # Dry run first
        print("━━━ Dry run ━━━")
        with open(AUDIO_FILE, "rb") as f:
            resp = await client.post(
                "/v1/voice/commands",
                files={"audio": (AUDIO_FILE, f, "audio/mpeg")},
                data={"mode": "dry_run", "timezone": "Europe/Vienna", "locale": "de-AT"},
            )
        print_response(resp)

        # Execute
        print("\n━━━ Execute ━━━")
        with open(AUDIO_FILE, "rb") as f:
            resp = await client.post(
                "/v1/voice/commands",
                files={"audio": (AUDIO_FILE, f, "audio/mpeg")},
                data={"mode": "execute", "timezone": "Europe/Vienna", "locale": "de-AT"},
            )
        print_response(resp)


if __name__ == "__main__":
    asyncio.run(main())
