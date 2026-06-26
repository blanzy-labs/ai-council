from typing import Any

from openai import OpenAI, OpenAIError

from app.core.config import Settings, get_settings
from app.models.provider import ProviderError, ProviderRequest, ProviderResponse
from app.providers.base import Provider


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(
        self,
        settings: Settings | None = None,
        client: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._client = client

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        api_key = self.settings.openai_api_key
        if not api_key:
            raise ProviderError(
                provider=self.name,
                message="OPENAI_API_KEY is not configured.",
                error_type="missing_api_key",
            )

        model = request.model or self.settings.openai_model
        client = self._client or OpenAI(
            api_key=api_key,
            timeout=self.settings.openai_timeout_seconds,
        )

        try:
            response = client.responses.create(
                model=model,
                instructions=request.system_prompt,
                input=self._build_input(request),
                max_output_tokens=self.settings.openai_max_output_tokens,
                store=False,
            )
        except OpenAIError as exc:
            raise ProviderError(
                provider=self.name,
                message="OpenAI request failed.",
                error_type=exc.__class__.__name__,
            ) from exc
        except Exception as exc:
            raise ProviderError(
                provider=self.name,
                message="OpenAI provider failed.",
                error_type=exc.__class__.__name__,
            ) from exc

        return ProviderResponse(
            provider=self.name,
            model=model,
            persona_id=request.persona_id,
            persona_name=request.persona_name,
            content=self._extract_content(response),
            raw_response_id=getattr(response, "id", None),
            usage=self._normalize_usage(getattr(response, "usage", None)),
            finish_reason=self._extract_finish_reason(response),
        )

    def _build_input(self, request: ProviderRequest) -> str:
        if request.context is None:
            return request.user_prompt

        if isinstance(request.context, str):
            return f"Context:\n{request.context}\n\nUser prompt:\n{request.user_prompt}"

        context_lines = [
            f"{message.get('role', 'context')}: {message.get('content', '')}"
            for message in request.context
        ]
        return (
            "Context messages:\n"
            + "\n".join(context_lines)
            + f"\n\nUser prompt:\n{request.user_prompt}"
        )

    def _extract_content(self, response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str):
            return output_text

        output = getattr(response, "output", None)
        if not output:
            return ""

        parts: list[str] = []
        for item in output:
            for content_item in getattr(item, "content", []) or []:
                text = getattr(content_item, "text", None)
                if isinstance(text, str):
                    parts.append(text)

        return "\n".join(parts)

    def _normalize_usage(self, usage: Any) -> dict[str, Any] | None:
        if usage is None:
            return None
        if isinstance(usage, dict):
            return usage
        if hasattr(usage, "model_dump"):
            return usage.model_dump()
        return None

    def _extract_finish_reason(self, response: Any) -> str | None:
        output = getattr(response, "output", None)
        if not output:
            return getattr(response, "status", None)

        for item in output:
            finish_reason = getattr(item, "finish_reason", None)
            if isinstance(finish_reason, str):
                return finish_reason

        status = getattr(response, "status", None)
        return status if isinstance(status, str) else None
