"""Quick script to test the Todoist voice command flow."""

import asyncio
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://127.0.0.1:8000"
API_KEY = os.environ.get("API_KEY", "YOUR_API_KEY")
TODOIST_TOKEN = os.environ.get("TODOIST_API_TOKEN", "")


def print_response(resp: httpx.Response):
    print(f"Status: {resp.status_code}")
    try:
        print(resp.json())
    except Exception:
        print(resp.text)


async def main():
    print(f"Using API_KEY: {API_KEY[:8]}...")
    async with httpx.AsyncClient(base_url=BASE_URL, headers={"X-API-Key": API_KEY}, timeout=30) as client:
        # Step 1: Connect Todoist token
        print("━━━ Step 1: Connecting Todoist token ━━━")
        resp = await client.post("/auth/todoist", json={"api_token": TODOIST_TOKEN})
        print_response(resp)
        if resp.status_code != 200:
            return

        # Step 2: Send a voice command
        print("\n━━━ Step 2: Sending voice command ━━━")
        command = "Remind me to buy groceries tomorrow priority 1 in project Besorgungen"
        print(f'Command: "{command}"\n')
        resp = await client.post("/voice", json={"text": command})
        print_response(resp)


if __name__ == "__main__":
    asyncio.run(main())
