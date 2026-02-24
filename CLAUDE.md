# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Voice command backend that receives voice commands from Apple Shortcuts, uses OpenAI to extract structured intent (validated with Pydantic), and routes actions to integrations (Google Calendar, Todoist). Multi-user support via API key authentication.

## Tech Stack

- **Language:** Python 3.12+, managed with `uv`
- **Framework:** FastAPI (async)
- **Database:** Postgres (Render) via async SQLAlchemy + Alembic migrations
- **LLM:** OpenAI API (`gpt-4o`) with `response_format=json_object`
- **Google OAuth 2.0** for Calendar and Gmail integrations
- **Credentials:** Fernet-encrypted tokens stored in Postgres

## Commands

```bash
# Install dependencies
uv sync

# Run dev server
uv run uvicorn app.main:app --reload

# Run tests
uv run pytest tests/ -v

# Run a single test
uv run pytest tests/test_crypto.py::test_encrypt_decrypt_roundtrip -v

# Alembic migrations
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

## Architecture

```
Apple Shortcut → POST /voice → Auth (X-API-Key) → LLM Parsing → Action Router → Integration Services → JSON Response
```

### Key modules

- **`app/config.py`** — `pydantic-settings` Settings singleton (all env vars)
- **`app/db.py`** — Async SQLAlchemy engine/session, `Base` declarative base, `get_db` dependency
- **`app/utils/auth.py`** — `get_current_user` dependency (looks up `X-API-Key` header in DB)
- **`app/utils/crypto.py`** — `encrypt()`/`decrypt()` using Fernet
- **`app/schemas/voice.py`** — Central Pydantic models: `VoiceRequest`, `ParsedIntent`, `CalendarIntent`, `TodoistIntent`, `VoiceResponse`
- **`app/services/llm.py`** — `parse_voice_command()` sends text to OpenAI, returns `ParsedIntent`
- **`app/services/router.py`** — `route_action()` dispatches to calendar/todoist handlers
- **`app/services/calendar.py`** — Google Calendar event creation via `google-api-python-client`
- **`app/services/todoist.py`** — Todoist task creation via REST API v2 with `httpx`
- **`app/routers/voice.py`** — `POST /voice` endpoint
- **`app/routers/auth.py`** — Google OAuth flow + Todoist token storage

### Data flow for `POST /voice`

1. `get_current_user` validates `X-API-Key` → `User` model
2. `parse_voice_command(text, timezone)` → OpenAI → `ParsedIntent`
3. `route_action(intent, user, db)` → dispatches to `handle_calendar_action` or `handle_todoist_action`
4. Integration handler fetches encrypted creds from `integrations` table, decrypts, calls external API
5. Returns `VoiceResponse` JSON

## Required Environment Variables

`DATABASE_URL`, `OPENAI_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `ENCRYPTION_KEY`

See `.env.example` for format. Generate a Fernet key with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Database

Two tables: `users` (with indexed `api_key`) and `integrations` (with `UNIQUE(user_id, service)`). Alembic manages migrations with async engine config in `alembic/env.py`.

## Google OAuth Flow

1. `GET /auth/google/start` — requires API key, redirects to Google consent screen
2. `GET /auth/google/callback` — public, exchanges code for refresh token, encrypts and upserts into `integrations`
3. At runtime, decrypt refresh token and use `google-auth` + `google-api-python-client`

## Notes

- `google-api-python-client` is synchronous — wrap in `asyncio.to_thread()` if latency becomes an issue
- Google OAuth uses `prompt=consent` to always get a refresh_token
- Todoist uses a simple encrypted personal API token (not OAuth)
