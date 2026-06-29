import asyncio
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import _session_event_stream, app
from app.models.events import CouncilEvent
from app.services.event_bus import EventBus, event_bus


client = TestClient(app)


def create_session(selected_persona_ids: list[str] | None = None) -> dict:
    response = client.post(
        "/sessions",
        json={
            "title": "Event test session",
            "topic": "Should event streaming work?",
            "mode": "ask_council",
            "selected_persona_ids": selected_persona_ids
            or ["moderator", "strategist", "skeptic"],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_event_model_serializes_correctly() -> None:
    event = CouncilEvent(
        id="evt-000001",
        session_id="session-0001",
        type="persona_started",
        status="started",
        message="Skeptic started.",
        persona_id="skeptic",
        persona_name="Skeptic",
        role="persona",
        provider="mock",
        model="mock-model",
        content=None,
        metadata={"round": 1},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert event.model_dump(mode="json") == {
        "id": "evt-000001",
        "session_id": "session-0001",
        "type": "persona_started",
        "status": "started",
        "message": "Skeptic started.",
        "persona_id": "skeptic",
        "persona_name": "Skeptic",
        "role": "persona",
        "provider": "mock",
        "model": "mock-model",
        "content": None,
        "metadata": {"round": 1},
        "created_at": "2026-01-01T00:00:00Z",
    }


def test_event_bus_stores_recent_events() -> None:
    bus = EventBus(buffer_size=2)

    bus.publish_event("session-0001", "run_started", "started", "one")
    second = bus.publish_event("session-0001", "persona_started", "started", "two")
    third = bus.publish_event("session-0001", "run_completed", "completed", "three")

    assert bus.list_events("session-0001") == [second, third]


def test_event_bus_list_events_returns_events_for_session() -> None:
    bus = EventBus()
    event = bus.publish_event(
        "session-0001",
        "chat_started",
        "started",
        "Chat started.",
    )

    assert bus.list_events("session-0001") == [event]
    assert bus.list_events("session-0002") == []


def test_run_publishes_expected_recent_events_with_mock_provider() -> None:
    session = create_session()

    response = client.post(
        f"/sessions/{session['id']}/run",
        json={
            "provider_override": "mock",
            "max_rounds": 1,
            "include_moderator_summary": True,
        },
    )
    assert response.status_code == 200

    events_response = client.get(f"/sessions/{session['id']}/events/recent")
    assert events_response.status_code == 200
    event_types = [event["type"] for event in events_response.json()]

    assert event_types[0] == "run_started"
    assert "persona_started" in event_types
    assert "persona_completed" in event_types
    assert "message_appended" in event_types
    assert "moderator_started" in event_types
    assert "moderator_completed" in event_types
    assert event_types[-1] == "run_completed"


def test_chat_publishes_expected_recent_events_with_mock_provider() -> None:
    session = create_session()

    response = client.post(
        f"/sessions/{session['id']}/chat",
        json={
            "message": "What is the riskiest assumption?",
            "target": {"type": "council"},
            "provider_override": "mock",
            "include_moderator_summary": True,
        },
    )
    assert response.status_code == 200

    events_response = client.get(f"/sessions/{session['id']}/events/recent")
    assert events_response.status_code == 200
    event_types = [event["type"] for event in events_response.json()]

    assert event_types[0] == "chat_started"
    assert "message_appended" in event_types
    assert "persona_started" in event_types
    assert "persona_completed" in event_types
    assert "moderator_started" in event_types
    assert "moderator_completed" in event_types
    assert event_types[-1] == "chat_completed"


def test_recent_events_endpoint_returns_events_after_run() -> None:
    session = create_session(selected_persona_ids=["skeptic"])
    run_response = client.post(
        f"/sessions/{session['id']}/run",
        json={
            "provider_override": "mock",
            "max_rounds": 1,
            "include_moderator_summary": False,
        },
    )
    assert run_response.status_code == 200

    response = client.get(f"/sessions/{session['id']}/events/recent")

    assert response.status_code == 200
    assert len(response.json()) > 0


def test_recent_events_unknown_session_returns_404() -> None:
    response = client.get("/sessions/session-9999/events/recent")

    assert response.status_code == 404


def test_event_stream_keeps_subscription_after_heartbeat() -> None:
    event_bus.publish_event(
        "session-0001",
        "run_started",
        "started",
        "Council run started.",
    )

    async def collect_stream_chunks() -> tuple[str, str, str]:
        stream = _session_event_stream("session-0001", heartbeat_seconds=0.01)
        try:
            first_event = await asyncio.wait_for(anext(stream), timeout=1)
            heartbeat = await asyncio.wait_for(anext(stream), timeout=1)
            event_bus.publish_event(
                "session-0001",
                "run_completed",
                "completed",
                "Council run completed.",
            )
            second_event = await asyncio.wait_for(anext(stream), timeout=1)
            return first_event, heartbeat, second_event
        finally:
            await stream.aclose()

    first_event, heartbeat, second_event = asyncio.run(collect_stream_chunks())

    assert "event: run_started" in first_event
    assert heartbeat == ": heartbeat\n\n"
    assert "event: run_completed" in second_event
