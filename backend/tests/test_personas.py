from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_list_personas_returns_default_personas() -> None:
    response = client.get("/personas")

    assert response.status_code == 200
    personas = response.json()
    persona_ids = [persona["id"] for persona in personas]

    assert persona_ids == [
        "moderator",
        "strategist",
        "skeptic",
        "builder",
        "ethicist",
        "customer_advocate",
        "contrarian",
    ]
    assert all(persona["provider"] == "openai" for persona in personas)
    assert all(persona["model"] == "default" for persona in personas)


def test_get_persona_returns_known_persona() -> None:
    response = client.get("/personas/moderator")

    assert response.status_code == 200
    persona = response.json()
    assert persona["id"] == "moderator"
    assert persona["name"] == "Moderator"
    assert "structured" in persona["system_prompt"]


def test_get_persona_returns_404_for_unknown_persona() -> None:
    response = client.get("/personas/unknown")

    assert response.status_code == 404
