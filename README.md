# AI Council

AI Council is a local-first Mythadis Labs app that will become a text-based multi-persona AI council room. This repository contains the v0.1.0 scaffold: a FastAPI backend, a React/Vite frontend, Docker Compose wiring, health checks, default personas, and in-memory council session creation.

## v0.1.0 Scope

- OpenAI-only configuration shape.
- No OpenAI API integration yet.
- Backend health endpoint at `/health`.
- Default persona registry exposed by the API.
- In-memory council session creation and lookup.
- Frontend landing page with backend health, persona cards, and a test session form.
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
- OpenAI API calls

No API key is required for the current slice.

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

## API Endpoints

- `GET /health`
- `GET /personas`
- `GET /personas/{persona_id}`
- `POST /sessions`
- `GET /sessions`
- `GET /sessions/{session_id}`

Example persona request:

```sh
curl http://localhost:8000/personas
```

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

Create a local environment file:

```sh
cp .env.example .env
```

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

## Docker Setup

Create a local environment file:

```sh
cp .env.example .env
```

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
- Sessions: http://localhost:8000/sessions

## Tests and Checks

Run backend tests:

```sh
cd backend
uv run pytest
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
