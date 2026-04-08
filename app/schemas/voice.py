from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, model_validator


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
    as_user: bool = False


class ParsedIntent(BaseModel):
    service: Literal["calendar", "todoist", "slack"]
    calendar: Optional[CalendarIntent] = None
    todoist: Optional[TodoistIntent] = None
    slack: Optional[SlackIntent] = None

    @model_validator(mode="after")
    def validate_service_field(self):
        field = getattr(self, self.service)
        if field is None:
            raise ValueError(
                f"service is '{self.service}' but {self.service} field is null"
            )
        others = {"calendar", "todoist", "slack"} - {self.service}
        for other in others:
            if getattr(self, other) is not None:
                raise ValueError(
                    f"service is '{self.service}' but {other} field is populated"
                )
        return self


class ParsedMultiIntent(BaseModel):
    intents: list[ParsedIntent]
    raw_text: str


class VoiceResponse(BaseModel):
    status: str
    service: str
    message: str
    details: Optional[dict] = None


class MultiVoiceResponse(BaseModel):
    status: str  # "success" | "partial" | "error"
    results: list[VoiceResponse]
