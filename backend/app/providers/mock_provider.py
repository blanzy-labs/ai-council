from app.models.provider import ProviderRequest, ProviderResponse
from app.providers.base import Provider


class MockProvider(Provider):
    name = "mock"

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        model = request.model or "mock-model"
        return ProviderResponse(
            provider=self.name,
            model=model,
            persona_id=request.persona_id,
            persona_name=request.persona_name,
            content=(
                f"[mock:{request.persona_id}] {request.persona_name} response "
                f"to: {request.user_prompt}"
            ),
            raw_response_id="mock-response-0001",
            usage={
                "input_chars": len(request.user_prompt),
                "output_chars": 0,
            },
            finish_reason="stop",
        )
