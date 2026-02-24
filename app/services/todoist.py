import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import Integration
from app.models.user import User
from app.schemas.voice import TodoistIntent, VoiceResponse
from app.utils.crypto import decrypt

logger = logging.getLogger(__name__)

TODOIST_BASE = "https://api.todoist.com/api/v1"
TODOIST_TASKS = f"{TODOIST_BASE}/tasks"
TODOIST_PROJECTS = f"{TODOIST_BASE}/projects"


async def _resolve_project_id(project_name: str, token: str) -> str | None:
    """Look up a Todoist project by name (case-insensitive) and return its ID."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            TODOIST_PROJECTS,
            headers={"Authorization": f"Bearer {token}"},
        )
    if resp.status_code != 200:
        logger.warning("Failed to fetch Todoist projects: %s", resp.text)
        return None

    data = resp.json()
    projects = data.get("results", data) if isinstance(data, dict) else data
    name_lower = project_name.lower()
    for project in projects:
        if project.get("name", "").lower() == name_lower:
            return project["id"]
    return None


async def handle_todoist_action(
    intent: TodoistIntent, user: User, db: AsyncSession
) -> VoiceResponse:
    result = await db.execute(
        select(Integration).where(
            Integration.user_id == user.id,
            Integration.service == "todoist",
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        return VoiceResponse(
            status="error",
            service="todoist",
            message="Todoist not connected. Use POST /auth/todoist to add your API token.",
        )

    token = decrypt(integration.encrypted_credentials)

    task_data: dict = {"content": intent.content}
    if intent.description:
        task_data["description"] = intent.description
    if intent.due_string:
        task_data["due_string"] = intent.due_string
    if intent.priority:
        task_data["priority"] = intent.priority
    if intent.labels:
        task_data["labels"] = intent.labels

    # Resolve project name to ID
    if intent.project:
        project_id = await _resolve_project_id(intent.project, token)
        if project_id:
            task_data["project_id"] = project_id
        else:
            logger.warning("Project '%s' not found, using Inbox", intent.project)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            TODOIST_TASKS,
            json=task_data,
            headers={"Authorization": f"Bearer {token}"},
        )

    if resp.status_code != 200:
        return VoiceResponse(
            status="error",
            service="todoist",
            message=f"Todoist API error: {resp.text}",
        )

    result_data = resp.json()
    return VoiceResponse(
        status="success",
        service="todoist",
        message=f"Task '{intent.content}' created",
        details={"task_id": result_data.get("id"), "url": result_data.get("url")},
    )
