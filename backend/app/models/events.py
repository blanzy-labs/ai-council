from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


CouncilEventType = Literal[
    "run_started",
    "chat_started",
    "persona_started",
    "persona_completed",
    "moderator_started",
    "moderator_completed",
    "message_appended",
    "error",
    "run_completed",
    "chat_completed",
]

CouncilEventStatus = Literal["started", "in_progress", "completed", "failed"]


class CouncilEvent(BaseModel):
    id: str
    session_id: str
    type: CouncilEventType
    status: CouncilEventStatus
    message: str
    persona_id: str | None = None
    persona_name: str | None = None
    role: str | None = None
    provider: str | None = None
    model: str | None = None
    content: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime
