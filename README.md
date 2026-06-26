# AI Council

AI Council is a local-first Mythadis Labs app that will become a text-based multi-persona AI council room. This repository contains the v0.1.0 scaffold: FastAPI backend, React/Vite frontend, Docker Compose wiring, health checks, default personas, in-memory sessions, provider adapters, a first non-streaming council orchestrator, and a simple chat room follow-up flow.

## v0.1.0 Scope

- OpenAI-only configuration shape.
- OpenAI provider adapter and deterministic mock provider.
- Default persona registry exposed by the API.
- In-memory council session creation, lookup, run results, and messages.
- Controlled non-streaming council runs for `ask_council`, `council_discussion`, and `ask_one`.
- Follow-up chat to ask the whole council or one selected persona.
- Frontend panels for health, personas, session creation, council runs, chat follow-ups, and provider testing.
- Local development and Docker Compose workflows.

Session, run, and chat transcript data is memory-only and resets when the backend process restarts.

## Intentionally Out of Scope

- Voice
- Gemini
- Login
- Database
- Telemetry
- Persistence
- Streaming
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

## API Endpoints

- `GET /health`
- `GET /personas`
- `GET /personas/{persona_id}`
- `POST /providers/test-generate`
- `POST /sessions`
- `GET /sessions`
- `GET /sessions/{session_id}`
- `POST /sessions/{session_id}/run`
- `POST /sessions/{session_id}/chat`
- `GET /sessions/{session_id}/result`
- `GET /sessions/{session_id}/messages`

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

Get the latest stored result:

```sh
curl http://localhost:8000/sessions/<SESSION_ID>/result
```

Get the latest stored messages:

```sh
curl http://localhost:8000/sessions/<SESSION_ID>/messages
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

- Non-streaming only
- In-memory only
- No voice
- No Gemini
- No persistence
- No open-ended agent loops
- No long-term chat history
- No authentication

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
