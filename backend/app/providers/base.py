from abc import ABC, abstractmethod

from app.models.provider import ProviderRequest, ProviderResponse


class Provider(ABC):
    name: str

    @abstractmethod
    def generate(self, request: ProviderRequest) -> ProviderResponse:
        raise NotImplementedError
