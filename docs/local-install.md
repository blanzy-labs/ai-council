# Local Install

## Prerequisites

- Git
- Docker Desktop or Docker Engine
- Python 3.13 and `uv`
- Node.js and `pnpm`
- OpenAI API key only if testing the OpenAI provider

## Clone

```sh
gh repo clone blanzy-labs/ai-council
cd ai-council
```

## Environment Setup

```sh
cp .env.example .env
```

Mock provider flows work without `OPENAI_API_KEY`. OpenAI calls require `OPENAI_API_KEY` in `.env` or the backend environment.

## Backend Local Setup

Run tests:

```sh
cd backend
uv run pytest
```

Start the backend:

```sh
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend Local Setup

Install dependencies and start the frontend:

```sh
cd frontend
pnpm install
pnpm dev
```

## Docker Setup

From the repo root:

```sh
docker compose up --build
```

Stop the stack:

```sh
docker compose down
```

## Expected URLs

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Version: http://localhost:8000/version

## Notes

- Normal tests and local mock flows do not require an OpenAI key.
- OpenAI provider calls require `OPENAI_API_KEY`.
- Runtime sessions, transcripts, and events are in memory only in v0.1.x.
- Do not commit `.env`.
