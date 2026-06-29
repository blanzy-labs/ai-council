from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.session import CouncilMode, SessionStatus


ExportFormat = Literal["markdown", "json"]


class ExportRequest(BaseModel):
    format: ExportFormat
    include_events: bool = False
    include_metadata: bool = True


class ExportMetadata(BaseModel):
    session_id: str
    title: str
    topic: str
    mode: CouncilMode
    status: SessionStatus
    selected_persona_ids: list[str]
    created_at: datetime
    updated_at: datetime
    exported_at: datetime
    message_count: int
    event_count: int | None = None


class ExportResponse(BaseModel):
    session_id: str
    format: ExportFormat
    filename: str
    content_type: str
    content: str


class TranscriptClearResponse(BaseModel):
    session_id: str
    cleared: bool
    message_count: int


class EventClearResponse(BaseModel):
    session_id: str
    cleared: bool
    event_count: int
