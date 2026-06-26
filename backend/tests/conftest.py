from collections.abc import Generator

import pytest

from app.services.session_store import session_store


@pytest.fixture(autouse=True)
def clear_session_store() -> Generator[None, None, None]:
    session_store.clear()
    yield
    session_store.clear()
