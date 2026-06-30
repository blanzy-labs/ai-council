from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app
from app.models.provider import ProviderError, ProviderRequest
from app.providers.factory import get_provider
from app.providers.mock_provider import MockProvider
from app.providers.openai_provider import OpenAIProvider


client = TestClient(app)


def test_mock_provider_returns_deterministic_response() -> None:
    provider = MockProvider()
    request = ProviderRequest(
        persona_id="skeptic",
        persona_name="Skeptic",
        system_prompt="Challenge assumptions.",
        user_prompt="What is the biggest risk?",
    )

    response = provider.generate(request)

    assert response.provider == "mock"
    assert response.model == "mock-model"
    assert response.persona_id == "skeptic"
    assert response.persona_name == "Skeptic"
    assert response.content == (
        "[mock:skeptic] Skeptic response to: What is the biggest risk?"
    )
    assert response.raw_response_id == "mock-response-0001"
    assert response.finish_reason == "stop"


def test_provider_factory_returns_mock_provider() -> None:
    provider = get_provider("mock")

    assert isinstance(provider, MockProvider)


def test_provider_factory_rejects_unknown_provider() -> None:
    with pytest.raises(ProviderError) as exc_info:
        get_provider("unknown")

    assert exc_info.value.error_type == "unsupported_provider"
    assert exc_info.value.provider == "unknown"


def test_test_generate_with_mock_provider_returns_normalized_response() -> None:
    response = client.post(
        "/providers/test-generate",
        json={
            "provider": "mock",
            "persona_id": "skeptic",
            "user_prompt": "What is the biggest risk in this idea?",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "mock"
    assert body["model"] == "mock-model"
    assert body["persona_id"] == "skeptic"
    assert body["persona_name"] == "Skeptic"
    assert body["content"] == (
        "[mock:skeptic] Skeptic response to: "
        "What is the biggest risk in this idea?"
    )


def test_test_generate_rejects_unknown_persona() -> None:
    response = client.post(
        "/providers/test-generate",
        json={
            "provider": "mock",
            "persona_id": "unknown",
            "user_prompt": "What is the biggest risk?",
        },
    )

    assert response.status_code == 404


def test_test_generate_rejects_empty_user_prompt() -> None:
    response = client.post(
        "/providers/test-generate",
        json={
            "provider": "mock",
            "persona_id": "skeptic",
            "user_prompt": "   ",
        },
    )

    assert response.status_code == 422


def test_test_generate_rejects_overly_long_user_prompt() -> None:
    response = client.post(
        "/providers/test-generate",
        json={
            "provider": "mock",
            "persona_id": "skeptic",
            "user_prompt": "x" * 4001,
        },
    )

    assert response.status_code == 422


def test_test_generate_with_openai_and_no_api_key_returns_clean_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.providers.openai_provider.get_settings",
        lambda: Settings(openai_api_key=None),
    )

    response = client.post(
        "/providers/test-generate",
        json={
            "provider": "openai",
            "persona_id": "skeptic",
            "user_prompt": "What is the biggest risk?",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "provider": "openai",
        "message": "OPENAI_API_KEY is not configured.",
        "error_type": "missing_api_key",
    }


class FakeResponses:
    def __init__(self) -> None:
        self.kwargs: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.kwargs = kwargs
        return SimpleNamespace(
            id="resp_test_123",
            output_text="A normalized OpenAI response.",
            usage={"input_tokens": 11, "output_tokens": 5},
            status="completed",
        )


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()


def test_openai_provider_uses_settings_and_normalizes_mocked_client_response() -> None:
    fake_client = FakeOpenAIClient()
    provider = OpenAIProvider(
        settings=Settings(
            openai_api_key="test-key",
            openai_model="gpt-test",
            openai_timeout_seconds=5,
            openai_max_output_tokens=123,
        ),
        client=fake_client,
    )
    request = ProviderRequest(
        persona_id="builder",
        persona_name="Builder",
        system_prompt="Build practical steps.",
        user_prompt="How should we proceed?",
    )

    response = provider.generate(request)

    assert fake_client.responses.kwargs == {
        "model": "gpt-test",
        "instructions": "Build practical steps.",
        "input": "How should we proceed?",
        "max_output_tokens": 123,
        "store": False,
    }
    assert response.provider == "openai"
    assert response.model == "gpt-test"
    assert response.persona_id == "builder"
    assert response.persona_name == "Builder"
    assert response.content == "A normalized OpenAI response."
    assert response.raw_response_id == "resp_test_123"
    assert response.usage == {"input_tokens": 11, "output_tokens": 5}
    assert response.finish_reason == "completed"
