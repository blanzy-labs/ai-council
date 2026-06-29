import json

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def create_session(selected_persona_ids: list[str] | None = None) -> dict:
    response = client.post(
        "/sessions",
        json={
            "title": "Export test session",
            "topic": "Should export and transcript management work?",
            "mode": "ask_council",
            "selected_persona_ids": selected_persona_ids or ["moderator", "skeptic"],
        },
    )
    assert response.status_code == 201
    return response.json()


def run_session(session_id: str) -> dict:
    response = client.post(
        f"/sessions/{session_id}/run",
        json={
            "provider_override": "mock",
            "max_rounds": 1,
            "include_moderator_summary": True,
        },
    )
    assert response.status_code == 200
    return response.json()


def export_session(session_id: str, body: dict | None = None) -> dict:
    response = client.post(
        f"/sessions/{session_id}/export",
        json=body
        or {
            "format": "markdown",
            "include_events": False,
            "include_metadata": True,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_markdown_export_works_for_session_with_messages() -> None:
    session = create_session()
    run_session(session["id"])

    export = export_session(session["id"])

    assert export["format"] == "markdown"
    assert export["content_type"] == "text/markdown"
    assert export["filename"].endswith(".md")
    assert "# AI Council Session: Export test session" in export["content"]
    assert "Should export and transcript management work?" in export["content"]
    assert "`ask_council`" in export["content"]
    assert "[mock:skeptic]" in export["content"]


def test_markdown_export_works_for_session_with_no_messages() -> None:
    session = create_session()

    export = export_session(session["id"])

    assert "## Transcript" in export["content"]
    assert "_No transcript messages yet._" in export["content"]


def test_json_export_works_for_session_with_messages() -> None:
    session = create_session()
    run_session(session["id"])

    export = export_session(
        session["id"],
        {
            "format": "json",
            "include_events": False,
            "include_metadata": True,
        },
    )
    payload = json.loads(export["content"])

    assert export["content_type"] == "application/json"
    assert payload["metadata"]["session_id"] == session["id"]
    assert payload["session"]["title"] == "Export test session"
    assert len(payload["messages"]) > 0
    assert payload["latest_result"]["session_id"] == session["id"]


def test_json_export_returns_valid_json_serializable_content() -> None:
    session = create_session()
    run_session(session["id"])

    export = export_session(
        session["id"],
        {
            "format": "json",
            "include_events": False,
            "include_metadata": True,
        },
    )

    payload = json.loads(export["content"])
    assert json.loads(json.dumps(payload)) == payload


def test_export_with_include_events_true_includes_recent_events() -> None:
    session = create_session()
    run_session(session["id"])

    export = export_session(
        session["id"],
        {
            "format": "json",
            "include_events": True,
            "include_metadata": True,
        },
    )
    payload = json.loads(export["content"])

    assert len(payload["recent_events"]) > 0
    assert payload["metadata"]["event_count"] == len(payload["recent_events"])


def test_unknown_session_export_returns_404() -> None:
    response = client.post(
        "/sessions/session-9999/export",
        json={
            "format": "markdown",
            "include_events": False,
            "include_metadata": True,
        },
    )

    assert response.status_code == 404


def test_unsupported_export_format_returns_validation_error() -> None:
    session = create_session()

    response = client.post(
        f"/sessions/{session['id']}/export",
        json={
            "format": "html",
            "include_events": False,
            "include_metadata": True,
        },
    )

    assert response.status_code == 422


def test_direct_markdown_download_endpoint_returns_markdown() -> None:
    session = create_session()
    run_session(session["id"])

    response = client.get(f"/sessions/{session['id']}/export/markdown")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.headers["content-disposition"].startswith("attachment;")
    assert response.text.startswith("# AI Council Session: Export test session")


def test_direct_json_download_endpoint_returns_json() -> None:
    session = create_session()
    run_session(session["id"])

    response = client.get(f"/sessions/{session['id']}/export/json")
    payload = response.json()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["content-disposition"].startswith("attachment;")
    assert payload["session"]["id"] == session["id"]


def test_delete_messages_clears_transcript() -> None:
    session = create_session()
    run_session(session["id"])

    response = client.delete(f"/sessions/{session['id']}/messages")
    export = export_session(
        session["id"],
        {
            "format": "json",
            "include_events": False,
            "include_metadata": True,
        },
    )
    payload = json.loads(export["content"])

    assert response.status_code == 200
    assert response.json() == {
        "session_id": session["id"],
        "cleared": True,
        "message_count": 0,
    }
    assert payload["messages"] == []
    assert "latest_result" not in payload


def test_delete_events_clears_recent_events() -> None:
    session = create_session()
    run_session(session["id"])

    response = client.delete(f"/sessions/{session['id']}/events")
    events_response = client.get(f"/sessions/{session['id']}/events/recent")

    assert response.status_code == 200
    assert response.json() == {
        "session_id": session["id"],
        "cleared": True,
        "event_count": 0,
    }
    assert events_response.status_code == 200
    assert events_response.json() == []
