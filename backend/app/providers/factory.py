from app.core.config import Settings
from app.models.provider import ProviderError
from app.providers.base import Provider
from app.providers.mock_provider import MockProvider
from app.providers.openai_provider import OpenAIProvider


def get_provider(provider_name: str, settings: Settings | None = None) -> Provider:
    normalized_provider = provider_name.strip().lower()

    if normalized_provider == "mock":
        return MockProvider()
    if normalized_provider == "openai":
        return OpenAIProvider(settings=settings)

    raise ProviderError(
        provider=normalized_provider or "unknown",
        message=f"Provider '{provider_name}' is not supported.",
        error_type="unsupported_provider",
    )
