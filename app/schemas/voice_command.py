from typing import Any, Literal

from pydantic import BaseModel


class IntentSummary(BaseModel):
    service: str | None = None
    action: str | None = None
    confidence: float | None = None
    entities: dict[str, Any] | None = None


class ExecutionSummary(BaseModel):
    status: Literal["succeeded", "failed", "skipped", "previewed"]
    provider: str | None = None
    provider_reference: str | None = None
    dry_run: bool = False


class LatencyBreakdown(BaseModel):
    total: int
    upload_parse: int | None = None
    transcription: int | None = None
    intent_parse: int | None = None
    execution: int | None = None
    response_build: int | None = None


class ErrorPayload(BaseModel):
    code: str
    message: str
    retryable: bool = False
    details: dict[str, Any] | None = None


class VoiceCommandResponse(BaseModel):
    ok: bool
    request_id: str
    mode: Literal["execute", "dry_run"]
    transcript: str | None = None
    normalized_text: str | None = None
    intent: IntentSummary | None = None
    execution: ExecutionSummary | None = None
    result_text: str
    error: ErrorPayload | None = None
    latency_ms: LatencyBreakdown
