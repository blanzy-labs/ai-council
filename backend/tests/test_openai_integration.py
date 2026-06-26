import os

import pytest

from app.models.provider import ProviderRequest
from app.providers.openai_provider import OpenAIProvider


@pytest.mark.integration
def test_openai_provider_real_smoke() -> None:
    if os.getenv("RUN_OPENAI_INTEGRATION_TESTS") != "1":
        pytest.skip("Set RUN_OPENAI_INTEGRATION_TESTS=1 to run this test.")
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("Set OPENAI_API_KEY to run this test.")

    provider = OpenAIProvider()
    response = provider.generate(
        ProviderRequest(
            persona_id="skeptic",
            persona_name="Skeptic",
            system_prompt="Answer in one short sentence.",
            user_prompt="Name one risk of adding too much scope.",
        )
    )

    assert response.provider == "openai"
    assert response.content
