from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app


client = TestClient(app)


def create_session(
    selected_persona_ids: list[str] | None = None,
    mode: str = "ask_council",
) -> dict:
    response = client.post(
        "/sessions",
        json={
            "title": "Chat follow-up test",
            "topic": "Should AI Council support follow-up chat?",
            "mode": mode,
            "selected_persona_ids": selected_persona_ids
            or ["moderator", "strategist", "skeptic", "builder"],
        },
    )
    assert response.status_code == 201
    return response.json()


def chat(session_id: str, body: dict | None = None) -> dict:
    response = client.post(
        f"/sessions/{session_id}/chat",
        json=body
        or {
            "message": "What is the riskiest assumption in this plan?",
            "target": {"type": "council"},
            "provider_override": "mock",
            "include_moderator_summary": False,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_chat_target_council_returns_user_message_and_persona_responses() -> None:
    session = create_session(
        selected_persona_ids=["moderator", "strategist", "skeptic", "builder"],
    )

    response = chat(session["id"])

    assert response["status"] == "completed"
    assert response["user_message"]["role"] == "user"
    assert response["user_message"]["content"] == (
        "What is the riskiest assumption in this plan?"
    )
    assert [message["persona_id"] for message in response["responses"]] == [
        "strategist",
        "skeptic",
        "builder",
    ]
    assert [message["role"] for message in response["messages"]] == [
        "user",
        "persona",
        "persona",
        "persona",
    ]


def test_chat_target_persona_returns_only_that_persona() -> None:
    session = create_session()

    response = chat(
        session["id"],
        {
            "message": "Builder, what is the smallest useful MVP?",
            "target": {"type": "persona", "persona_id": "builder"},
            "provider_override": "mock",
            "include_moderator_summary": False,
        },
    )

    assert len(response["responses"]) == 1
    assert response["responses"][0]["persona_id"] == "builder"
    assert response["summary"] is None


def test_chat_works_without_prior_run() -> None:
    session = create_session(selected_persona_ids=["skeptic"])

    response = chat(
        session["id"],
        {
            "message": "What should we validate first?",
            "target": {"type": "council"},
            "provider_override": "mock",
            "include_moderator_summary": False,
        },
    )

    assert response["status"] == "completed"
    assert [message["role"] for message in response["messages"]] == [
        "user",
        "persona",
    ]


def test_chat_appends_messages_to_existing_transcript() -> None:
    session = create_session(selected_persona_ids=["strategist", "skeptic"])

    first = chat(session["id"])
    second = chat(
        session["id"],
        {
            "message": "What should the next step be?",
            "target": {"type": "persona", "persona_id": "skeptic"},
            "provider_override": "mock",
            "include_moderator_summary": False,
        },
    )

    assert len(first["messages"]) == 3
    assert len(second["messages"]) == 5
    assert [message["id"] for message in second["messages"]] == [
        "msg-0001",
        "msg-0002",
        "msg-0003",
        "msg-0004",
        "msg-0005",
    ]


def test_messages_endpoint_returns_appended_chat_messages_after_run() -> None:
    session = create_session(selected_persona_ids=["moderator", "builder"])
    run_response = client.post(
        f"/sessions/{session['id']}/run",
        json={
            "provider_override": "mock",
            "max_rounds": 1,
            "include_moderator_summary": True,
        },
    )
    assert run_response.status_code == 200

    response = chat(
        session["id"],
        {
            "message": "What should we build first?",
            "target": {"type": "persona", "persona_id": "builder"},
            "provider_override": "mock",
            "include_moderator_summary": False,
        },
    )
    messages_response = client.get(f"/sessions/{session['id']}/messages")

    assert messages_response.status_code == 200
    assert messages_response.json() == response["messages"]
    assert len(messages_response.json()) == 5


def test_chat_target_persona_rejects_persona_not_selected() -> None:
    session = create_session(selected_persona_ids=["skeptic"])

    response = client.post(
        f"/sessions/{session['id']}/chat",
        json={
            "message": "Builder, what should we build first?",
            "target": {"type": "persona", "persona_id": "builder"},
            "provider_override": "mock",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["persona_id"] == "builder"


def test_chat_target_persona_rejects_missing_persona_id() -> None:
    session = create_session()

    response = client.post(
        f"/sessions/{session['id']}/chat",
        json={
            "message": "Who should answer?",
            "target": {"type": "persona"},
            "provider_override": "mock",
        },
    )

    assert response.status_code == 422


def test_chat_unknown_session_returns_404() -> None:
    response = client.post(
        "/sessions/session-9999/chat",
        json={
            "message": "Is anyone there?",
            "target": {"type": "council"},
            "provider_override": "mock",
        },
    )

    assert response.status_code == 404


def test_chat_rejects_empty_message() -> None:
    session = create_session()

    response = client.post(
        f"/sessions/{session['id']}/chat",
        json={
            "message": "   ",
            "target": {"type": "council"},
            "provider_override": "mock",
        },
    )

    assert response.status_code == 422


def test_chat_rejects_overly_long_message() -> None:
    session = create_session()

    response = client.post(
        f"/sessions/{session['id']}/chat",
        json={
            "message": "x" * 4001,
            "target": {"type": "council"},
            "provider_override": "mock",
        },
    )

    assert response.status_code == 422


def test_chat_rejects_unsupported_provider_override() -> None:
    session = create_session()

    response = client.post(
        f"/sessions/{session['id']}/chat",
        json={
            "message": "What next?",
            "target": {"type": "council"},
            "provider_override": "unsupported",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error_type"] == "unsupported_provider"


def test_chat_with_moderator_summary_returns_summary_when_moderator_selected() -> None:
    session = create_session(selected_persona_ids=["moderator", "builder"])

    response = chat(
        session["id"],
        {
            "message": "What should we do next?",
            "target": {"type": "council"},
            "provider_override": "mock",
            "include_moderator_summary": True,
        },
    )

    assert response["summary"] is not None
    assert response["summary"]["role"] == "moderator"
    assert response["summary"]["persona_id"] == "moderator"
    assert [message["role"] for message in response["messages"]] == [
        "user",
        "persona",
        "moderator",
    ]


def test_chat_with_openai_without_api_key_fails_gracefully(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.providers.openai_provider.get_settings",
        lambda: Settings(openai_api_key=None),
    )
    session = create_session(selected_persona_ids=["skeptic"])

    response = chat(
        session["id"],
        {
            "message": "What is risky?",
            "target": {"type": "council"},
            "provider_override": "openai",
            "include_moderator_summary": False,
        },
    )

    assert response["status"] == "failed"
    assert response["responses"] == []
    assert response["errors"][0]["error_type"] == "missing_api_key"
