from fastapi.testclient import TestClient

from app.main import app
from app.models.provider import ProviderError, ProviderRequest, ProviderResponse
from app.providers.mock_provider import MockProvider


client = TestClient(app)


def create_session(
    mode: str = "ask_council",
    selected_persona_ids: list[str] | None = None,
) -> dict:
    response = client.post(
        "/sessions",
        json={
            "title": "Council run test",
            "topic": "Should AI Council stay local-first?",
            "mode": mode,
            "selected_persona_ids": selected_persona_ids
            or ["moderator", "strategist", "skeptic", "builder"],
        },
    )
    assert response.status_code == 201
    return response.json()


def run_session(session_id: str, body: dict | None = None) -> dict:
    response = client.post(
        f"/sessions/{session_id}/run",
        json=body
        or {
            "provider_override": "mock",
            "max_rounds": 1,
            "include_moderator_summary": True,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_ask_council_with_mock_provider_returns_topic_and_persona_messages() -> None:
    session = create_session(
        selected_persona_ids=["strategist", "skeptic", "builder"],
    )

    result = run_session(
        session["id"],
        {
            "provider_override": "mock",
            "max_rounds": 1,
            "include_moderator_summary": False,
        },
    )

    assert result["status"] == "completed"
    assert result["mode"] == "ask_council"
    assert [message["role"] for message in result["messages"]] == [
        "user",
        "persona",
        "persona",
        "persona",
    ]
    assert result["messages"][0]["content"] == "Should AI Council stay local-first?"
    assert [message["persona_id"] for message in result["messages"][1:]] == [
        "strategist",
        "skeptic",
        "builder",
    ]
    assert all(message["provider"] == "mock" for message in result["messages"][1:])


def test_ask_council_with_moderator_selected_returns_summary() -> None:
    session = create_session()

    result = run_session(session["id"])

    assert result["summary"]
    assert result["messages"][-1]["role"] == "moderator"
    assert result["messages"][-1]["persona_id"] == "moderator"
    assert result["messages"][-1]["content"] == result["summary"]


def test_ask_council_without_moderator_still_works() -> None:
    session = create_session(selected_persona_ids=["strategist", "skeptic"])

    result = run_session(session["id"])

    assert result["status"] == "completed"
    assert result["summary"] is None
    assert [message["role"] for message in result["messages"]] == [
        "user",
        "persona",
        "persona",
    ]


def test_council_discussion_caps_max_rounds_at_two() -> None:
    session = create_session(
        mode="council_discussion",
        selected_persona_ids=["strategist", "skeptic"],
    )

    result = run_session(
        session["id"],
        {
            "provider_override": "mock",
            "max_rounds": 5,
            "include_moderator_summary": False,
        },
    )

    persona_messages = [
        message for message in result["messages"] if message["role"] == "persona"
    ]
    assert len(persona_messages) == 4
    assert [message["metadata"]["round"] for message in persona_messages] == [
        1,
        1,
        2,
        2,
    ]


def test_ask_one_uses_one_non_moderator_persona() -> None:
    session = create_session(
        mode="ask_one",
        selected_persona_ids=["moderator", "skeptic", "builder"],
    )

    result = run_session(
        session["id"],
        {
            "provider_override": "mock",
            "max_rounds": 2,
            "include_moderator_summary": False,
        },
    )

    persona_messages = [
        message for message in result["messages"] if message["role"] == "persona"
    ]
    assert len(persona_messages) == 1
    assert persona_messages[0]["persona_id"] == "skeptic"


def test_run_unknown_session_returns_404() -> None:
    response = client.post(
        "/sessions/session-9999/run",
        json={"provider_override": "mock"},
    )

    assert response.status_code == 404


def test_run_unsupported_provider_override_returns_clean_error() -> None:
    session = create_session()

    response = client.post(
        f"/sessions/{session['id']}/run",
        json={"provider_override": "unsupported"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error_type"] == "unsupported_provider"


def test_result_endpoint_returns_stored_result_after_run() -> None:
    session = create_session()
    result = run_session(session["id"])

    response = client.get(f"/sessions/{session['id']}/result")

    assert response.status_code == 200
    assert response.json() == result


def test_messages_endpoint_returns_stored_messages_after_run() -> None:
    session = create_session()
    result = run_session(session["id"])

    response = client.get(f"/sessions/{session['id']}/messages")

    assert response.status_code == 200
    assert response.json() == result["messages"]


class PartiallyFailingProvider:
    name = "mock"

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        if request.persona_id == "skeptic":
            raise ProviderError(
                provider="mock",
                message="Test provider failure.",
                error_type="test_failure",
            )
        return MockProvider().generate(request)


def test_persona_provider_failure_is_recorded_and_run_continues(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.council_orchestrator.get_provider",
        lambda provider_name: PartiallyFailingProvider(),
    )
    session = create_session(selected_persona_ids=["strategist", "skeptic"])

    result = run_session(
        session["id"],
        {
            "provider_override": "mock",
            "max_rounds": 1,
            "include_moderator_summary": False,
        },
    )

    assert result["status"] == "completed"
    assert len(result["errors"]) == 1
    assert result["errors"][0]["persona_id"] == "skeptic"
    assert result["errors"][0]["error_type"] == "test_failure"
    assert [message["persona_id"] for message in result["messages"]] == [
        "user",
        "strategist",
    ]
