# AI Council

AI Council is a local-first Mythadis Labs app that will become a text-based multi-persona AI council room. This repository contains the v0.1.0 scaffold: FastAPI backend, React/Vite frontend, Docker Compose wiring, health checks, default personas, in-memory sessions, provider adapters, a first non-streaming council orchestrator, simple chat room follow-ups, and event-level live transcript updates.

## v0.1.0 Scope

- Local-first, in-memory text council for public testing and demos.
- Provider support: OpenAI and deterministic mock.
- Mock mode for testing without `OPENAI_API_KEY`.
- OpenAI-only configuration shape.
- OpenAI provider adapter and deterministic mock provider.
- Default persona registry exposed by the API.
- In-memory council session creation, lookup, run results, and messages.
- Controlled non-streaming council runs for `ask_council`, `council_discussion`, and `ask_one`.
- Follow-up chat to ask the whole council or one selected persona.
- Server-Sent Events for live run/chat activity updates.
- Markdown and JSON exports for the current in-memory session transcript.
- Transcript and recent event clearing for the current in-memory session.
- Frontend panels for health, personas, session creation, council runs, live activity, chat follow-ups, exports, transcript management, and provider testing.
- Local development and Docker Compose workflows.

Session, run, and chat transcript data is memory-only and resets when the backend process restarts.

## UI Workflow

1. Create a session.
2. Run council.
3. Continue chat.
4. Export.

## Intentionally Out of Scope

- Voice
- Gemini
- Login
- Database
- Telemetry
- Persistence
- Token-level provider streaming
- Long-term history
- Open-ended agent loops

The app starts without `OPENAI_API_KEY`. Mock provider tests and mock council runs do not require an API key.

## Configuration

Copy the example environment file:

```sh
cp .env.example .env
```

Provider-related settings:

- `OPENAI_API_KEY=` optional unless manually testing real OpenAI calls
- `OPENAI_MODEL=gpt-4.1-mini`
- `OPENAI_TIMEOUT_SECONDS=30`
- `OPENAI_MAX_OUTPUT_TOKENS=700`

Missing `OPENAI_API_KEY` is handled gracefully by the OpenAI provider and does not prevent app startup.

## Personas

The backend includes seven default personas:

- `moderator`
- `strategist`
- `skeptic`
- `builder`
- `ethicist`
- `customer_advocate`
- `contrarian`

Each persona has `id`, `name`, `role`, `provider`, `model`, `system_prompt`, `goals`, and `constraints`. For v0.1.0, every default persona uses `provider: openai` and `model: default`; mock runs can override the provider at runtime.

## Sessions

Council sessions are stored in memory and include:

- `id`
- `title`
- `topic`
- `mode`
- `selected_persona_ids`
- `status`
- `created_at`
- `updated_at`

Supported modes:

- `ask_council`: each selected non-moderator persona responds once; moderator can summarize.
- `council_discussion`: two controlled rounds max; moderator can summarize.
- `ask_one`: the first selected non-moderator persona responds; moderator summary is optional.

Supported statuses:

- `created`
- `active`
- `completed`
- `failed`

## Provider Abstraction

The backend has a simple provider interface:

- `ProviderRequest` carries persona identity, system prompt, user prompt, optional context, and optional model override.
- `ProviderResponse` normalizes provider name, model, persona identity, content, raw response ID, usage, and finish reason.
- `MockProvider` returns deterministic fake content for tests and local development.
- `OpenAIProvider` uses the official OpenAI Python SDK, applies configured timeout and max output tokens, sends persona behavior through instructions, sets `store=False`, and normalizes the response.

Normal tests do not call OpenAI.

## Council Orchestrator

`POST /sessions/{session_id}/run` executes the selected session through the provider layer and returns a normalized `CouncilRunResult`:

- `session_id`
- `status`
- `mode`
- `topic`
- `messages`
- `summary`
- `errors`
- `created_at`
- `completed_at`

Each `CouncilMessage` includes:

- `id`
- `session_id`
- `persona_id`
- `persona_name`
- `role`
- `provider`
- `model`
- `content`
- `created_at`
- `metadata`

If one persona call fails, the run records an error and continues where possible. Unsupported provider overrides return a clean API error. Real OpenAI runs fail gracefully when `OPENAI_API_KEY` is missing.

## Chat Room Follow-up Flow

`POST /sessions/{session_id}/chat` appends a user follow-up message to the session transcript, calls either the whole council or one selected persona, appends the responses, and returns the full updated message list.

Chat targets:

- `council`: each selected non-moderator persona responds once.
- `persona`: only the selected `persona_id` responds.

Optional moderator summaries are generated only when `include_moderator_summary=true` and the moderator is selected for the session. Chat works even if no prior council run has been executed; the original session topic is still included in prompt context.

Context is compacted before provider calls. The current backend uses the latest 12 messages with a maximum context budget of about 6000 characters, with each message shortened before inclusion.

## Event Streaming

`GET /sessions/{session_id}/events` opens a Server-Sent Events stream for a session. The stream emits JSON `CouncilEvent` payloads for run and chat activity.

This is event-level streaming only. v0.1.0 does not stream provider tokens. Provider calls still complete as normal, then emit structured events such as persona completion and message append.

Recent events are buffered in memory per session:

- `GET /sessions/{session_id}/events/recent`
- buffer size: latest 100 events per session
- storage: in-memory only

Supported event types:

- `run_started`
- `chat_started`
- `persona_started`
- `persona_completed`
- `moderator_started`
- `moderator_completed`
- `message_appended`
- `error`
- `run_completed`
- `chat_completed`

Supported event statuses:

- `started`
- `in_progress`
- `completed`
- `failed`

## Export and Transcript Management

Exports are generated from the current backend process memory. Restarting or refreshing the backend loses sessions, messages, events, and exportable transcript state.

`POST /sessions/{session_id}/export` returns an inline export response with:

- `session_id`
- `format`
- `filename`
- `content_type`
- `content`

Supported export formats:

- `markdown`: clean Markdown with title, metadata, transcript, optional errors, and optional recent events.
- `json`: JSON content with session, messages, optional metadata, optional recent events, and latest run result when available.

Export options:

- `include_events`: include the current recent event buffer.
- `include_metadata`: include session/export metadata.

Direct download endpoints:

- `GET /sessions/{session_id}/export/markdown`
- `GET /sessions/{session_id}/export/json`

Transcript management endpoints:

- `DELETE /sessions/{session_id}/messages`: clears messages and the latest stored run result for that session.
- `DELETE /sessions/{session_id}/events`: clears the recent event buffer for that session.

## API Endpoints

- `GET /health`
- `GET /`
- `GET /version`
- `GET /personas`
- `GET /personas/{persona_id}`
- `POST /providers/test-generate`
- `POST /sessions`
- `GET /sessions`
- `GET /sessions/{session_id}`
- `POST /sessions/{session_id}/run`
- `POST /sessions/{session_id}/chat`
- `GET /sessions/{session_id}/events`
- `GET /sessions/{session_id}/events/recent`
- `DELETE /sessions/{session_id}/events`
- `POST /sessions/{session_id}/export`
- `GET /sessions/{session_id}/export/markdown`
- `GET /sessions/{session_id}/export/json`
- `GET /sessions/{session_id}/result`
- `GET /sessions/{session_id}/messages`
- `DELETE /sessions/{session_id}/messages`

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

Run a session with the mock provider:

```sh
curl -X POST http://localhost:8000/sessions/<SESSION_ID>/run \
  -H "Content-Type: application/json" \
  -d '{
    "provider_override": "mock",
    "max_rounds": 1,
    "include_moderator_summary": true
  }'
```

Run a session with OpenAI:

```sh
curl -X POST http://localhost:8000/sessions/<SESSION_ID>/run \
  -H "Content-Type: application/json" \
  -d '{
    "provider_override": "openai",
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

Ask the council with moderator summary:

```sh
curl -X POST http://localhost:8000/sessions/<SESSION_ID>/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What should we do next?",
    "target": {
      "type": "council"
    },
    "provider_override": "mock",
    "include_moderator_summary": true
  }'
```

Get recent events:

```sh
curl http://localhost:8000/sessions/<SESSION_ID>/events/recent
```

Open a live SSE stream:

```sh
curl -N http://localhost:8000/sessions/<SESSION_ID>/events
```

Run a council in another terminal while the SSE stream is open:

```sh
curl -X POST http://localhost:8000/sessions/<SESSION_ID>/run \
  -H "Content-Type: application/json" \
  -d '{
    "provider_override": "mock",
    "max_rounds": 1,
    "include_moderator_summary": true
  }'
```

Get the latest stored result:

```sh
curl http://localhost:8000/sessions/<SESSION_ID>/result
```

Get the latest stored messages:

```sh
curl http://localhost:8000/sessions/<SESSION_ID>/messages
```

Create an inline Markdown export:

```sh
curl -X POST http://localhost:8000/sessions/<SESSION_ID>/export \
  -H "Content-Type: application/json" \
  -d '{
    "format": "markdown",
    "include_events": false,
    "include_metadata": true
  }'
```

Download Markdown:

```sh
curl -OJ http://localhost:8000/sessions/<SESSION_ID>/export/markdown
```

Download JSON:

```sh
curl -OJ http://localhost:8000/sessions/<SESSION_ID>/export/json
```

Clear transcript messages:

```sh
curl -X DELETE http://localhost:8000/sessions/<SESSION_ID>/messages
```

Clear recent events:

```sh
curl -X DELETE http://localhost:8000/sessions/<SESSION_ID>/events
```

Backend metadata:

```sh
curl http://localhost:8000/
curl http://localhost:8000/version
```

Mock provider test:

```sh
curl -X POST http://localhost:8000/providers/test-generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "mock",
    "persona_id": "skeptic",
    "user_prompt": "What is the biggest risk in this idea?"
  }'
```

## v0.1.0 Limits

- Event-level streaming only
- No token-by-token provider streaming
- In-memory only
- Export content is generated from current runtime memory
- Backend restart loses sessions, messages, events, and export state
- No voice
- No Gemini
- No telemetry
- No persistence
- No open-ended agent loops
- No long-term chat history
- No authentication
- Voice is planned for v0.2.0, not v0.1.0
- Gemini provider support is planned for v0.3.0, not v0.1.0

## Troubleshooting

Backend unreachable:

- Confirm the API is running at http://localhost:8000.
- Check `curl http://localhost:8000/health`.
- If using Docker, confirm Docker is running and use `docker compose ps`.

Docker not running:

- Start Docker Desktop or your Docker daemon, then rerun `docker compose up --build`.

Ports already in use:

- Stop the process using port `8000` or `5173`, or change the exposed ports in Docker Compose for local testing.

OpenAI key missing:

- Mock mode works without a key.
- Real OpenAI calls require `OPENAI_API_KEY` in your environment or `.env`.
- Missing keys return a clean API error and do not prevent app startup.

Frontend cannot reach backend:

- Confirm `VITE_API_BASE_URL` points to the backend if you changed defaults.
- Local default is `http://localhost:8000`.

Sessions disappeared after restart:

- This is expected in v0.1.0. Sessions, messages, events, and exports are generated from runtime memory only.

## Local Setup

Install backend dependencies and run the API:

```sh
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Install frontend dependencies and run Vite:

```sh
cd frontend
pnpm install
pnpm dev
```

Expected local URLs:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Backend health: http://localhost:8000/health
- Personas: http://localhost:8000/personas
- Sessions: http://localhost:8000/sessions
- Provider test: http://localhost:8000/providers/test-generate

## Docker Setup

Build and start both services:

```sh
docker compose up --build
```

Stop services:

```sh
docker compose down
```

Expected Docker URLs:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Backend health: http://localhost:8000/health

## Tests and Checks

Run backend tests:

```sh
cd backend
uv run pytest
```

The real OpenAI smoke test is skipped unless both `OPENAI_API_KEY` and `RUN_OPENAI_INTEGRATION_TESTS=1` are set:

```sh
cd backend
RUN_OPENAI_INTEGRATION_TESTS=1 OPENAI_API_KEY=sk-... uv run pytest tests/test_openai_integration.py -m integration
```

Build the frontend:

```sh
cd frontend
pnpm build
```

Build and run with Docker Compose:

```sh
docker compose up --build
```
