from typing import Any

from pydantic import BaseModel, Field, field_validator


ProviderContext = str | list[dict[str, str]]


class ProviderRequest(BaseModel):
    persona_id: str = Field(min_length=1)
    persona_name: str = Field(min_length=1)
    system_prompt: str = Field(min_length=1)
    user_prompt: str = Field(min_length=1)
    context: ProviderContext | None = None
    model: str | None = None

    @field_validator("persona_id", "persona_name", "system_prompt", "user_prompt")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Value must not be empty.")
        return stripped

    @field_validator("model")
    @classmethod
    def normalize_optional_model(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ProviderResponse(BaseModel):
    provider: str
    model: str
    persona_id: str
    persona_name: str
    content: str
    raw_response_id: str | None = None
    usage: dict[str, Any] | None = None
    finish_reason: str | None = None


class ProviderTestGenerateRequest(BaseModel):
    provider: str | None = None
    persona_id: str = Field(min_length=1)
    user_prompt: str = Field(min_length=1)
    model: str | None = None

    @field_validator("provider", "model")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("persona_id", "user_prompt")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Value must not be empty.")
        return stripped


class ProviderError(Exception):
    def __init__(self, provider: str, message: str, error_type: str) -> None:
        super().__init__(message)
        self.provider = provider
        self.message = message
        self.error_type = error_type
