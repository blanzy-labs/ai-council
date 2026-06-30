from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


CouncilMode = Literal["ask_council", "council_discussion", "ask_one"]
SessionStatus = Literal["created", "active", "completed", "failed"]


class CouncilSessionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    topic: str = Field(min_length=1, max_length=4000)
    mode: CouncilMode
    selected_persona_ids: list[str] = Field(min_length=1)

    @field_validator("title", "topic")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Value must not be empty.")
        return stripped

    @field_validator("selected_persona_ids")
    @classmethod
    def require_non_empty_persona_ids(cls, value: list[str]) -> list[str]:
        cleaned = [persona_id.strip() for persona_id in value if persona_id.strip()]
        if not cleaned:
            raise ValueError("At least one persona must be selected.")
        return cleaned


class CouncilSession(BaseModel):
    id: str
    title: str
    topic: str
    mode: CouncilMode
    selected_persona_ids: list[str]
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
