from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_returns_service_status() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ai-council-backend",
    }


def test_root_returns_app_metadata() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "ai-council-backend",
        "version": "0.1.0",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
    }


def test_version_returns_scope_metadata() -> None:
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {
        "service": "ai-council",
        "version": "0.1.0",
        "provider_support": ["openai", "mock"],
        "voice": False,
        "gemini": False,
        "persistence": False,
    }
