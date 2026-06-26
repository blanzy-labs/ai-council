from collections.abc import Generator

import pytest

from app.services.session_store import session_store
from app.services.event_bus import event_bus
from app.services.transcript_store import transcript_store


@pytest.fixture(autouse=True)
def clear_session_store() -> Generator[None, None, None]:
    session_store.clear()
    event_bus.clear()
    transcript_store.clear()
    yield
    session_store.clear()
    event_bus.clear()
    transcript_store.clear()
