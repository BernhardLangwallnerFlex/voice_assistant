from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class VoiceRequest(BaseModel):
    text: str


class CalendarIntent(BaseModel):
    action: str = "create_event"
    title: str
    start_datetime: datetime
    end_datetime: datetime
    location: Optional[str] = None
    description: Optional[str] = None
    invitees: Optional[list[str]] = None


class TodoistIntent(BaseModel):
    action: str = "create_task"
    content: str
    description: Optional[str] = None
    due_string: Optional[str] = None
    priority: Optional[int] = None  # API: 4=urgent/p1, 3=high/p2, 2=medium/p3, 1=normal/p4
    project: Optional[str] = None  # project name (resolved to ID at runtime)
    labels: Optional[list[str]] = None


class SlackIntent(BaseModel):
    action: str = "send_message"
    recipient_name: str
    recipient_email: str
    message: str


class ParsedIntent(BaseModel):
    service: str  # "calendar" | "todoist" | "slack"
    calendar: Optional[CalendarIntent] = None
    todoist: Optional[TodoistIntent] = None
    slack: Optional[SlackIntent] = None
    raw_text: str


class VoiceResponse(BaseModel):
    status: str
    service: str
    message: str
    details: Optional[dict] = None
