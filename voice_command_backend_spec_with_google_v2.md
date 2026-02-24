# Voice Command Backend -- Updated Technical Specification (With Google OAuth)

## Overview

This system: - Receives voice commands via Apple Shortcuts - Uses an LLM
to extract structured intent - Routes actions to integrations (Todoist,
Google Calendar, Email, Mem) - Supports multiple users via API key
authentication - Uses OAuth 2.0 for Google integrations - Stores
encrypted credentials in Postgres

Language: Python Framework: FastAPI Database: Postgres (Render)

------------------------------------------------------------------------

# High-Level Architecture

Apple Shortcut → POST /voice → Authentication Layer → LLM Parsing Layer
→ Action Router → Integration Services → JSON Response

------------------------------------------------------------------------

# Required Environment Variables

GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET GOOGLE_REDIRECT_URI OPENAI_API_KEY
DATABASE_URL ENCRYPTION_KEY

------------------------------------------------------------------------

# Google OAuth 2.0 Flow

1.  User hits /auth/google/start
2.  Redirect to Google consent screen
3.  Google redirects back to /auth/google/callback
4.  Backend exchanges authorization code for refresh_token
5.  Store encrypted refresh_token in integrations table
6.  Use refresh_token to generate access tokens automatically

------------------------------------------------------------------------

# FastAPI Google OAuth Endpoints

## Start OAuth Flow

``` python
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode
import os

router = APIRouter()

GOOGLE_AUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"

@router.get("/auth/google/start")
async def google_auth_start(user=Depends(get_current_user)):

    params = {
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "redirect_uri": os.environ["GOOGLE_REDIRECT_URI"],
        "response_type": "code",
        "scope": " ".join([
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/gmail.send"
        ]),
        "access_type": "offline",
        "prompt": "consent",
        "state": str(user.id)
    }

    url = f"{GOOGLE_AUTH_BASE}?{urlencode(params)}"
    return RedirectResponse(url)
```

------------------------------------------------------------------------

## OAuth Callback

``` python
from fastapi import Request, HTTPException
import httpx
import os
from app.utils.crypto import encrypt

TOKEN_URL = "https://oauth2.googleapis.com/token"

@router.get("/auth/google/callback")
async def google_auth_callback(request: Request):

    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code:
        raise HTTPException(status_code=400, detail="Missing code")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": os.environ["GOOGLE_CLIENT_ID"],
                "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
                "redirect_uri": os.environ["GOOGLE_REDIRECT_URI"],
                "grant_type": "authorization_code",
            },
        )

    token_data = response.json()

    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token returned")

    encrypted = encrypt(refresh_token)

    save_google_integration(
        user_id=state,
        encrypted_credentials=encrypted
    )

    return {"status": "Google connected successfully"}
```

------------------------------------------------------------------------

# Using Google Calendar API at Runtime

``` python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from app.utils.crypto import decrypt
import os

def get_google_calendar_service(refresh_token):

    credentials = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
    )

    service = build("calendar", "v3", credentials=credentials)
    return service
```

------------------------------------------------------------------------

# Creating a Calendar Event

``` python
async def create_event(user, command):

    integration = get_user_integration(user.id, "google")
    refresh_token = decrypt(integration.encrypted_credentials)

    service = get_google_calendar_service(refresh_token)

    event = {
        "summary": command.title,
        "location": command.location,
        "description": command.body,
        "start": {
            "dateTime": command.start_datetime.isoformat(),
            "timeZone": user.timezone,
        },
        "end": {
            "dateTime": command.end_datetime.isoformat(),
            "timeZone": user.timezone,
        },
        "attendees": [
            {"email": email} for email in (command.invitees or [])
        ],
    }

    service.events().insert(
        calendarId="primary",
        body=event
    ).execute()
```

------------------------------------------------------------------------

# Security Notes

-   Store only encrypted refresh_token
-   Never store access_token
-   Use access_type=offline
-   Use prompt=consent for first authorization
-   Handle revoked tokens by forcing re-authentication

------------------------------------------------------------------------

# Integration Table Schema

``` sql
CREATE TABLE integrations (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    service TEXT NOT NULL,
    encrypted_credentials TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, service)
);
```

For Google: encrypted_credentials stores a JSON object containing the
refresh_token.
