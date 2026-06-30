from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


VALID_SESSION_REQUEST = {
    "title": "Launch review",
    "topic": "Should AI Council v0.1.0 include chat orchestration?",
    "mode": "ask_council",
    "selected_persona_ids": [
        "moderator",
        "strategist",
        "skeptic",
        "builder",
    ],
}


def create_valid_session() -> dict[str, object]:
    response = client.post("/sessions", json=VALID_SESSION_REQUEST)
    assert response.status_code == 201
    return response.json()


def test_create_session_accepts_valid_request() -> None:
    session = create_valid_session()

    assert session["id"] == "session-0001"
    assert session["title"] == VALID_SESSION_REQUEST["title"]
    assert session["topic"] == VALID_SESSION_REQUEST["topic"]
    assert session["mode"] == VALID_SESSION_REQUEST["mode"]
    assert session["selected_persona_ids"] == VALID_SESSION_REQUEST["selected_persona_ids"]
    assert session["status"] == "created"
    assert isinstance(session["created_at"], str)
    assert isinstance(session["updated_at"], str)


def test_create_session_rejects_unknown_persona_ids() -> None:
    request = {
        **VALID_SESSION_REQUEST,
        "selected_persona_ids": ["moderator", "unknown_persona"],
    }

    response = client.post("/sessions", json=request)

    assert response.status_code == 400
    assert response.json()["detail"]["unknown_persona_ids"] == ["unknown_persona"]


def test_create_session_rejects_unsupported_mode() -> None:
    request = {
        **VALID_SESSION_REQUEST,
        "mode": "unsupported_mode",
    }

    response = client.post("/sessions", json=request)

    assert response.status_code == 422


def test_create_session_rejects_overly_long_title() -> None:
    request = {
        **VALID_SESSION_REQUEST,
        "title": "x" * 121,
    }

    response = client.post("/sessions", json=request)

    assert response.status_code == 422


def test_create_session_rejects_overly_long_topic() -> None:
    request = {
        **VALID_SESSION_REQUEST,
        "topic": "x" * 4001,
    }

    response = client.post("/sessions", json=request)

    assert response.status_code == 422


def test_create_session_rejects_more_personas_than_available() -> None:
    request = {
        **VALID_SESSION_REQUEST,
        "selected_persona_ids": [
            "moderator",
            "strategist",
            "skeptic",
            "builder",
            "ethicist",
            "customer_advocate",
            "contrarian",
            "another_persona",
        ],
    }

    response = client.post("/sessions", json=request)

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "Too many personas selected."


def test_get_session_returns_created_session() -> None:
    created = create_valid_session()

    response = client.get(f"/sessions/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_session_returns_404_for_unknown_session() -> None:
    response = client.get("/sessions/session-9999")

    assert response.status_code == 404


def test_list_sessions_returns_created_sessions() -> None:
    first = create_valid_session()
    second_request = {
        **VALID_SESSION_REQUEST,
        "title": "Second session",
        "mode": "ask_one",
        "selected_persona_ids": ["builder"],
    }
    second_response = client.post("/sessions", json=second_request)
    assert second_response.status_code == 201

    response = client.get("/sessions")

    assert response.status_code == 200
    assert response.json() == [first, second_response.json()]
