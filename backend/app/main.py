import asyncio
import json
import os
from collections.abc import AsyncGenerator
from contextlib import suppress

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.models.chat import ChatRequest, ChatResponse
from app.models.council import CouncilMessage, CouncilRunRequest, CouncilRunResult
from app.models.events import CouncilEvent
from app.models.persona import Persona
from app.models.provider import (
    ProviderError,
    ProviderRequest,
    ProviderResponse,
    ProviderTestGenerateRequest,
)
from app.models.session import CouncilSession, CouncilSessionCreate
from app.providers.factory import get_provider
from app.services.chat_orchestrator import ChatOrchestrator
from app.services.council_orchestrator import CouncilOrchestrator
from app.services.event_bus import event_bus
from app.services.persona_registry import persona_registry
from app.services.session_store import session_store
from app.services.transcript_store import transcript_store


SSE_HEARTBEAT_SECONDS = 15.0


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


@app.post("/providers/test-generate", response_model=ProviderResponse)
def test_generate_provider(
    test_request: ProviderTestGenerateRequest,
) -> ProviderResponse:
    persona = persona_registry.get_persona(test_request.persona_id)
    if persona is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona '{test_request.persona_id}' not found.",
        )

    provider_name = test_request.provider or persona.provider
    model = test_request.model
    if model is None and persona.model != "default":
        model = persona.model

    try:
        provider = get_provider(provider_name)
        return provider.generate(
            ProviderRequest(
                persona_id=persona.id,
                persona_name=persona.name,
                system_prompt=persona.system_prompt,
                user_prompt=test_request.user_prompt,
                model=model,
            )
        )
    except ProviderError as exc:
        if exc.error_type == "missing_api_key":
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif exc.error_type == "unsupported_provider":
            status_code = status.HTTP_400_BAD_REQUEST
        else:
            status_code = status.HTTP_502_BAD_GATEWAY

        raise HTTPException(
            status_code=status_code,
            detail={
                "provider": exc.provider,
                "message": exc.message,
                "error_type": exc.error_type,
            },
        ) from exc


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


@app.post("/sessions/{session_id}/run", response_model=CouncilRunResult)
def run_session(
    session_id: str,
    run_request: CouncilRunRequest,
) -> CouncilRunResult:
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    if run_request.provider_override is not None:
        try:
            get_provider(run_request.provider_override)
        except ProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "provider": exc.provider,
                    "message": exc.message,
                    "error_type": exc.error_type,
                },
            ) from exc

    active_session = session_store.update_status(session_id, "active") or session
    orchestrator = CouncilOrchestrator(
        persona_registry=persona_registry,
        event_bus=event_bus,
    )
    result = orchestrator.run(active_session, run_request)
    transcript_store.save_run_result(session_id, result)
    session_store.update_status(session_id, result.status)

    return result


@app.post("/sessions/{session_id}/chat", response_model=ChatResponse)
def chat_session(
    session_id: str,
    chat_request: ChatRequest,
) -> ChatResponse:
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    if chat_request.provider_override is not None:
        try:
            get_provider(chat_request.provider_override)
        except ProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "provider": exc.provider,
                    "message": exc.message,
                    "error_type": exc.error_type,
                },
            ) from exc

    if chat_request.target.type == "persona":
        persona_id = chat_request.target.persona_id
        if persona_id not in session.selected_persona_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Target persona is not selected for this session.",
                    "persona_id": persona_id,
                },
            )

        if persona_id is not None and persona_registry.get_persona(persona_id) is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Target persona does not exist.",
                    "persona_id": persona_id,
                },
            )

    orchestrator = ChatOrchestrator(
        persona_registry=persona_registry,
        transcript_store=transcript_store,
        event_bus=event_bus,
    )
    return orchestrator.chat(session, chat_request)


@app.get("/sessions/{session_id}/events/recent", response_model=list[CouncilEvent])
def get_recent_session_events(session_id: str) -> list[CouncilEvent]:
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    return event_bus.list_events(session_id)


def _format_sse_event(event: CouncilEvent) -> str:
    payload = json.dumps(event.model_dump(mode="json"))
    return f"event: {event.type}\ndata: {payload}\n\n"


async def _session_event_stream(
    session_id: str,
    heartbeat_seconds: float = SSE_HEARTBEAT_SECONDS,
) -> AsyncGenerator[str, None]:
    subscription = event_bus.subscribe(session_id, include_recent=True)
    next_event_task = asyncio.create_task(anext(subscription))

    try:
        while True:
            done, _ = await asyncio.wait(
                {next_event_task},
                timeout=heartbeat_seconds,
            )
            if not done:
                yield ": heartbeat\n\n"
                continue

            try:
                event = next_event_task.result()
            except StopAsyncIteration:
                return

            yield _format_sse_event(event)
            next_event_task = asyncio.create_task(anext(subscription))
    except asyncio.CancelledError:
        return
    finally:
        if not next_event_task.done():
            next_event_task.cancel()
            with suppress(asyncio.CancelledError, StopAsyncIteration):
                await next_event_task
        with suppress(RuntimeError):
            await subscription.aclose()


@app.get("/sessions/{session_id}/events")
async def stream_session_events(session_id: str) -> StreamingResponse:
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    return StreamingResponse(
        _session_event_stream(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.get("/sessions/{session_id}/result", response_model=CouncilRunResult)
def get_session_result(session_id: str) -> CouncilRunResult:
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    result = transcript_store.get_run_result(session_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No result exists for session '{session_id}'.",
        )

    return result


@app.get("/sessions/{session_id}/messages", response_model=list[CouncilMessage])
def get_session_messages(session_id: str) -> list[CouncilMessage]:
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    messages = transcript_store.list_messages(session_id)
    if messages is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No messages exist for session '{session_id}'.",
        )

    return messages


@app.get("/sessions/{session_id}", response_model=CouncilSession)
def get_session(session_id: str) -> CouncilSession:
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )
    return session
