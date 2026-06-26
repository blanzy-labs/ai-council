from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.models.session import CouncilMode, SessionStatus


CouncilMessageRole = Literal["user", "persona", "moderator", "system"]


class CouncilMessage(BaseModel):
    id: str
    session_id: str
    persona_id: str
    persona_name: str
    role: CouncilMessageRole
    provider: str | None = None
    model: str | None = None
    content: str
    created_at: datetime
    metadata: dict[str, Any] | None = None


class CouncilRunRequest(BaseModel):
    provider_override: str | None = None
    max_rounds: int | None = Field(default=None, ge=1)
    include_moderator_summary: bool = True

    @field_validator("provider_override")
    @classmethod
    def normalize_provider_override(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip().lower()
        return stripped or None


class CouncilRunResult(BaseModel):
    session_id: str
    status: SessionStatus
    mode: CouncilMode
    topic: str
    messages: list[CouncilMessage]
    summary: str | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    completed_at: datetime
