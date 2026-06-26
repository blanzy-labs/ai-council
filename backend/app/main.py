import os

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.models.persona import Persona
from app.models.session import CouncilSession, CouncilSessionCreate
from app.services.persona_registry import persona_registry
from app.services.session_store import session_store


def _cors_origins() -> list[str]:
    frontend_port = os.getenv("FRONTEND_PORT", "5173")
    configured_origins = os.getenv("CORS_ORIGINS")

    origins = [
        f"http://localhost:{frontend_port}",
        f"http://127.0.0.1:{frontend_port}",
    ]

    if configured_origins:
        origins.extend(
            origin.strip()
            for origin in configured_origins.split(",")
            if origin.strip()
        )

    return origins


app = FastAPI(title="AI Council Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "ai-council-backend",
    }


@app.get("/personas", response_model=list[Persona])
def list_personas() -> list[Persona]:
    return persona_registry.list_personas()


@app.get("/personas/{persona_id}", response_model=Persona)
def get_persona(persona_id: str) -> Persona:
    persona = persona_registry.get_persona(persona_id)
    if persona is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona '{persona_id}' not found.",
        )
    return persona


@app.post(
    "/sessions",
    response_model=CouncilSession,
    status_code=status.HTTP_201_CREATED,
)
def create_session(session_create: CouncilSessionCreate) -> CouncilSession:
    unknown_persona_ids = persona_registry.unknown_persona_ids(
        session_create.selected_persona_ids
    )
    if unknown_persona_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Unknown persona IDs selected.",
                "unknown_persona_ids": unknown_persona_ids,
            },
        )

    return session_store.create_session(session_create)


@app.get("/sessions", response_model=list[CouncilSession])
def list_sessions() -> list[CouncilSession]:
    return session_store.list_sessions()


@app.get("/sessions/{session_id}", response_model=CouncilSession)
def get_session(session_id: str) -> CouncilSession:
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )
    return session
