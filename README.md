# AI Council

AI Council is a local-first Mythadis Labs app that will become a text-based multi-persona AI council room. This repository contains the v0.1.0 scaffold: a FastAPI backend, a React/Vite frontend, Docker Compose wiring, health checks, default personas, in-memory council session creation, and a clean provider adapter layer.

## v0.1.0 Scope

- OpenAI-only configuration shape.
- OpenAI provider adapter for manual testing.
- Mock provider for deterministic local and test use.
- Backend health endpoint at `/health`.
- Default persona registry exposed by the API.
- In-memory council session creation and lookup.
- Frontend landing page with backend health, persona cards, test session form, and provider test panel.
- Local development and Docker Compose workflows.

Session data is memory-only for now and resets when the backend process restarts.

## Intentionally Out of Scope

- Voice
- Gemini
- Login
- Database
- Telemetry
- Persistence
- Real chat orchestration
- Streaming
- Council-room OpenAI orchestration

The app starts without `OPENAI_API_KEY`. Mock provider testing does not require an API key.

## Configuration

Copy the example environment file:

```sh
cp .env.example .env
```

Provider-related settings:

- `OPENAI_API_KEY=` optional unless manually testing the real OpenAI provider
- `OPENAI_MODEL=gpt-4.1-mini`
- `OPENAI_TIMEOUT_SECONDS=30`
- `OPENAI_MAX_OUTPUT_TOKENS=700`

The backend loads these settings at runtime. Missing `OPENAI_API_KEY` is handled gracefully by the OpenAI provider and does not prevent app startup.

## Personas

The backend includes seven default personas:

- `moderator`
- `strategist`
- `skeptic`
- `builder`
- `ethicist`
- `customer_advocate`
- `contrarian`

Each persona has:

- `id`
- `name`
- `role`
- `provider`
- `model`
- `system_prompt`
- `goals`
- `constraints`

For v0.1.0, every default persona uses `provider: openai` and `model: default`. The moderator focuses on keeping the discussion structured, summarizing key points, identifying disagreements, and not dominating the discussion.

## Session Model

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

- `ask_council`
- `council_discussion`
- `ask_one`

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

Real OpenAI calls are only available through the manual provider test endpoint in this slice. They are not wired into sessions or council orchestration yet.

## API Endpoints

- `GET /health`
- `GET /personas`
- `GET /personas/{persona_id}`
- `POST /providers/test-generate`
- `POST /sessions`
- `GET /sessions`
- `GET /sessions/{session_id}`

Example persona request:

```sh
curl http://localhost:8000/personas
```

Example mock provider test:

```sh
curl -X POST http://localhost:8000/providers/test-generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "mock",
    "persona_id": "skeptic",
    "user_prompt": "What is the biggest risk in this idea?"
  }'
```

Example OpenAI provider test:

```sh
curl -X POST http://localhost:8000/providers/test-generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "persona_id": "skeptic",
    "user_prompt": "What is the biggest risk in this idea?"
  }'
```

If `OPENAI_API_KEY` is missing, the OpenAI provider returns a clean error instead of failing app startup.

Example session creation:

```sh
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Launch review",
    "topic": "Should AI Council v0.1.0 include chat orchestration?",
    "mode": "ask_council",
    "selected_persona_ids": [
      "moderator",
      "strategist",
      "skeptic",
      "builder"
    ]
  }'
```

Example session list:

```sh
curl http://localhost:8000/sessions
```

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
- Provider test: http://localhost:8000/providers/test-generate
- Sessions: http://localhost:8000/sessions

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
- Personas: http://localhost:8000/personas
- Provider test: http://localhost:8000/providers/test-generate
- Sessions: http://localhost:8000/sessions

## Tests and Checks

Run backend tests:

```sh
cd backend
uv run pytest
```

Normal tests do not call OpenAI. The real OpenAI smoke test is skipped unless both `OPENAI_API_KEY` and `RUN_OPENAI_INTEGRATION_TESTS=1` are set:

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
