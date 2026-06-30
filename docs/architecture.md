# Architecture Notes

## High-Level Architecture

AI Council v0.1.0 is a local app with a FastAPI backend, React/Vite frontend, provider adapters, in-memory stores, Server-Sent Events, and export generation.

```text
React/Vite frontend
        |
        | HTTP + SSE
        v
FastAPI backend
        |
        +-- persona registry
        +-- provider factory
        +-- council/chat orchestrators
        +-- in-memory session store
        +-- in-memory transcript store
        +-- in-memory event bus
        +-- export service
```

## Backend Components

- `app.main`: FastAPI routes, app metadata, CORS, health/version endpoints.
- `models`: Pydantic request/response models.
- `providers`: mock and OpenAI provider adapters.
- `services/persona_registry.py`: default personas.
- `services/session_store.py`: in-memory sessions.
- `services/transcript_store.py`: in-memory messages and latest run result.
- `services/event_bus.py`: in-memory recent event buffer and SSE subscribers.
- `services/council_orchestrator.py`: controlled council run flow.
- `services/chat_orchestrator.py`: follow-up chat flow.
- `services/export_service.py`: Markdown and JSON export generation.

## Frontend Components

- `src/App.tsx`: main app state, API calls, SSE subscription, panels, transcript, activity, chat, exports, and provider test UI.
- `src/styles.css`: dark local-first app styling and responsive layout rules.

## Provider Abstraction

Providers expose a common `generate` interface and return normalized `ProviderResponse` objects. The mock provider is deterministic and used for tests/local flows. The OpenAI provider is optional and requires `OPENAI_API_KEY`.

## Persona Registry

The registry is static in v0.1.0 and supplies the default personas. Sessions reference personas by ID.

## Session Store

Sessions are stored in process memory only. Restarting the backend clears all sessions.

## Transcript Store

Messages and latest run results are stored in process memory only. Clearing transcript removes messages and the latest stored run result for that session.

## Event Bus And SSE

The event bus stores a small recent buffer per session and supports subscribers through `GET /sessions/{session_id}/events`. This is event-level streaming, not token-level model streaming.

## Export Service

Exports are generated from the current in-memory session, messages, latest result, and optional recent events. No export files are persisted by the backend.

## Why No Database In v0.1.0

The first release is intentionally local-first and lightweight. In-memory storage keeps setup simple, avoids migrations, and makes the behavior easy to inspect during public testing.

## Future Gemini Provider

Gemini can be added later by implementing a provider adapter that matches the existing provider interface and registering it in the provider factory.

## Future Voice Work

Voice can be layered onto the existing transcript model by treating speech input/output as another way to create and consume messages, while keeping the core session/transcript structure stable.
