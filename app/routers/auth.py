import json
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.models.integration import Integration
from app.models.user import User
from app.utils.auth import get_current_user
from app.utils.crypto import encrypt

router = APIRouter(prefix="/auth")

GOOGLE_AUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


@router.get("/google/start")
async def google_auth_start(user: User = Depends(get_current_user)):
    settings = get_settings()
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(
            [
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/gmail.send",
            ]
        ),
        "access_type": "offline",
        "prompt": "consent",
        "state": str(user.id),
    }
    url = f"{GOOGLE_AUTH_BASE}?{urlencode(params)}"
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_auth_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    settings = get_settings()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )

    token_data = response.json()
    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token returned")

    encrypted = encrypt(json.dumps({"refresh_token": refresh_token}))

    # Upsert: update if exists, insert if not
    result = await db.execute(
        select(Integration).where(
            Integration.user_id == state,
            Integration.service == "google",
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.encrypted_credentials = encrypted
    else:
        db.add(
            Integration(
                user_id=state,
                service="google",
                encrypted_credentials=encrypted,
            )
        )
    await db.commit()

    return {"status": "Google connected successfully"}


class TodoistTokenRequest(BaseModel):
    api_token: str


@router.post("/todoist")
async def connect_todoist(
    body: TodoistTokenRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    encrypted = encrypt(body.api_token)

    result = await db.execute(
        select(Integration).where(
            Integration.user_id == user.id,
            Integration.service == "todoist",
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.encrypted_credentials = encrypted
    else:
        db.add(
            Integration(
                user_id=user.id,
                service="todoist",
                encrypted_credentials=encrypted,
            )
        )
    await db.commit()

    return {"status": "Todoist connected successfully"}
