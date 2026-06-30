# AI Council

A local-first, text-based multi-persona AI council room for structured discussion, critique, follow-up chat, live activity events, and transcript export.

**Version:** v0.1.0 - Local Council MVP

AI Council v0.1.0 is intended for local testing, demos, and iteration. It runs with a deterministic mock provider by default for safe local workflows, and can call OpenAI only when explicitly configured and selected.

## Current Scope

- OpenAI provider support
- Mock provider for local testing without `OPENAI_API_KEY`
- Multi-persona council sessions
- Default personas
- Structured council run
- Follow-up chat
- Ask whole council
- Ask one persona
- Server-Sent Events live activity events
- Markdown export
- JSON export
- In-memory sessions/transcripts/events only
- Docker Compose local run

## Out Of Scope For v0.1.0

- Voice
- Gemini
- Database persistence
- User accounts
- Telemetry
- Hosted deployment
- Long-term session history
- Token-by-token model streaming
- Autonomous/open-ended agent loops

## Roadmap

- v0.2.0: voice experiments using OpenAI only
- v0.3.0: Gemini provider adapter exploration

## Architecture Overview

- FastAPI backend exposes personas, sessions, council runs, chat, events, exports, health, and version metadata.
- React/Vite frontend provides the local app UI.
- Provider adapter layer normalizes mock and OpenAI responses behind one interface.
- Persona registry provides the default council personas.
- In-memory session, transcript, and event stores hold runtime state only.
- SSE event stream powers live activity updates.
- Export service generates Markdown and JSON from the current in-memory session state.
- Docker Compose runs backend and frontend together for local validation.

There is no database in v0.1.0. Restarting the backend loses sessions, transcripts, events, and exportable state.

## Local Setup

Prerequisites:

- Python 3.13
- `uv`
- Node.js and `pnpm`
- Docker Desktop or Docker daemon, if using Docker Compose

Copy the example environment file:

```sh
cp .env.example .env
```

Only set `OPENAI_API_KEY` if you are manually testing OpenAI. Mock mode and normal tests do not require an API key.

Backend:

```sh
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```sh
cd frontend
pnpm install
pnpm dev
```

Local URLs:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Version: http://localhost:8000/version

## Docker Setup

Build and start both services:

```sh
docker compose up --build
```

Expected URLs:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Health: http://localhost:8000/health

Stop services:

```sh
docker compose down
```

## Testing

Backend tests:

```sh
cd backend
uv run pytest
```

Frontend build:

```sh
cd frontend
pnpm build
```

Docker build:

```sh
docker compose build
```

Optional real OpenAI smoke test:

```sh
cd backend
# Set OPENAI_API_KEY in your shell first.
RUN_OPENAI_INTEGRATION_TESTS=1 uv run pytest tests/test_openai_integration.py -m integration
```

Normal tests skip real OpenAI calls.

## Usage Workflow

1. Create session.
2. Select personas.
3. Run council.
4. Continue chat.
5. Watch live activity.
6. Export transcript.

Recommended local testing path: use `provider_override: "mock"` in run/chat requests, or select `mock` in the frontend.

## API Summary

- `GET /`
- `GET /health`
- `GET /version`
- `GET /personas`
- `GET /personas/{persona_id}`
- `POST /providers/test-generate`
- `POST /sessions`
- `GET /sessions`
- `GET /sessions/{session_id}`
- `POST /sessions/{session_id}/run`
- `POST /sessions/{session_id}/chat`
- `GET /sessions/{session_id}/messages`
- `DELETE /sessions/{session_id}/messages`
- `GET /sessions/{session_id}/events`
- `GET /sessions/{session_id}/events/recent`
- `DELETE /sessions/{session_id}/events`
- `GET /sessions/{session_id}/result`
- `POST /sessions/{session_id}/export`
- `GET /sessions/{session_id}/export/markdown`
- `GET /sessions/{session_id}/export/json`

## Curl Examples

Metadata:

```sh
curl http://localhost:8000/
curl http://localhost:8000/health
curl http://localhost:8000/version
```

Create a session:

```sh
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Local-first AI Council",
    "topic": "Should AI Council be built as a local-first multi-persona app?",
    "mode": "ask_council",
    "selected_persona_ids": [
      "moderator",
      "strategist",
      "skeptic",
      "builder",
      "customer_advocate"
    ]
  }'
```

Run council with mock:

```sh
curl -X POST http://localhost:8000/sessions/<SESSION_ID>/run \
  -H "Content-Type: application/json" \
  -d '{
    "provider_override": "mock",
    "max_rounds": 1,
    "include_moderator_summary": true
  }'
```

Ask the whole council:

```sh
curl -X POST http://localhost:8000/sessions/<SESSION_ID>/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the riskiest assumption in this plan?",
    "target": {
      "type": "council"
    },
    "provider_override": "mock",
    "include_moderator_summary": false
  }'
```

Ask one persona:

```sh
curl -X POST http://localhost:8000/sessions/<SESSION_ID>/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the smallest useful MVP?",
    "target": {
      "type": "persona",
      "persona_id": "builder"
    },
    "provider_override": "mock",
    "include_moderator_summary": false
  }'
```

Recent events:

```sh
curl http://localhost:8000/sessions/<SESSION_ID>/events/recent
```

Live SSE stream:

```sh
curl -N http://localhost:8000/sessions/<SESSION_ID>/events
```

Inline Markdown export:

```sh
curl -X POST http://localhost:8000/sessions/<SESSION_ID>/export \
  -H "Content-Type: application/json" \
  -d '{
    "format": "markdown",
    "include_events": false,
    "include_metadata": true
  }'
```

Inline JSON export:

```sh
curl -X POST http://localhost:8000/sessions/<SESSION_ID>/export \
  -H "Content-Type: application/json" \
  -d '{
    "format": "json",
    "include_events": true,
    "include_metadata": true
  }'
```

Direct downloads:

```sh
curl -OJ http://localhost:8000/sessions/<SESSION_ID>/export/markdown
curl -OJ http://localhost:8000/sessions/<SESSION_ID>/export/json
```

Clear runtime state:

```sh
curl -X DELETE http://localhost:8000/sessions/<SESSION_ID>/messages
curl -X DELETE http://localhost:8000/sessions/<SESSION_ID>/events
```

## Troubleshooting

Docker Desktop not running:

- Start Docker Desktop or your Docker daemon.
- Rerun `docker compose up --build`.

Ports `8000` or `5173` already in use:

- Stop the process using the port, or adjust `BACKEND_PORT` / `FRONTEND_PORT` in `.env`.

Frontend cannot reach backend:

- Confirm backend health: `curl http://localhost:8000/health`.
- Confirm `VITE_API_BASE_URL=http://localhost:8000`.
- If using Docker, run `docker compose ps`.

OpenAI key missing:

- Mock mode works without a key.
- Real OpenAI calls require `OPENAI_API_KEY`.
- Missing keys return a clean API error and do not prevent app startup.

Mock works but OpenAI fails:

- Confirm `OPENAI_API_KEY` is set in `.env` or the backend environment.
- Confirm the selected provider is `openai`.
- Check backend logs for provider errors.

Sessions disappear after restart:

- Expected in v0.1.0. Runtime state is in memory only.

CORS/local URL issues:

- Default allowed frontend origins are `http://localhost:5173` and `http://127.0.0.1:5173`.
- Add comma-separated local origins with `CORS_ORIGINS` if needed.

## Release Docs

- [v0.1.0 scope](docs/v0.1.0-scope.md)
- [release notes](docs/release-notes/v0.1.0.md)
- [GitHub release notes](docs/github-release-notes.md)
- [demo guide](docs/demo.md)
- [validation checklist](docs/validation/v0.1.0-validation.md)
- [architecture notes](docs/architecture.md)
- [security and privacy notes](docs/security-and-privacy.md)
- [sample scenarios](docs/sample-scenarios.md)
- [release checklist](docs/release-checklist.md)
