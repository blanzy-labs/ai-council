from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.council import CouncilMessage


ChatTargetType = Literal["council", "persona"]


class ChatTarget(BaseModel):
    type: ChatTargetType
    persona_id: str | None = None

    @field_validator("persona_id")
    @classmethod
    def normalize_persona_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def require_persona_id_for_persona_target(self) -> "ChatTarget":
        if self.type == "persona" and self.persona_id is None:
            raise ValueError("persona_id is required when target.type is persona.")
        return self


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    target: ChatTarget
    provider_override: str | None = None
    include_moderator_summary: bool = False

    @field_validator("message")
    @classmethod
    def require_non_empty_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Message must not be empty.")
        return stripped

    @field_validator("provider_override")
    @classmethod
    def normalize_provider_override(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip().lower()
        return stripped or None


class ChatResponse(BaseModel):
    session_id: str
    status: str
    user_message: CouncilMessage
    responses: list[CouncilMessage]
    summary: CouncilMessage | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)
    messages: list[CouncilMessage]
