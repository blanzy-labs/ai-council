# v0.1.0 - Local Council MVP

AI Council v0.1.0 is a local-first, text-based multi-persona council room for structured discussion, critique, follow-up chat, live activity events, and transcript export.

## Highlights

- Local FastAPI backend and React/Vite frontend
- OpenAI provider adapter plus deterministic mock provider
- Default persona registry
- Multi-persona council sessions
- Controlled council run flow
- Follow-up chat with whole-council and one-persona targets
- Server-Sent Events live activity stream
- Markdown and JSON transcript export
- Transcript and recent event clearing
- Docker Compose local workflow

## What Is Included

- Health, root, and version endpoints
- Persona and session APIs
- Council run and chat APIs
- Recent event and SSE endpoints
- Export endpoints for inline and downloadable content
- In-memory session, transcript, and event stores
- Backend test suite and frontend build validation
- Release docs, validation checklist, security/privacy notes, architecture notes, and demo guide

## Intentionally Excluded

- Voice
- Gemini
- Database persistence
- User accounts or login
- Telemetry
- Hosted deployment
- Long-term session history
- Token-by-token model streaming
- Autonomous/open-ended agent loops

## How To Run Locally

```sh
cp .env.example .env
docker compose up --build
```

Then open:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs

Mock mode works without an OpenAI API key. Add `OPENAI_API_KEY` only if manually testing OpenAI.

## Known Limitations

- Runtime state is in memory only.
- Restarting the backend clears sessions, transcripts, and events.
- Streaming is event-level only.
- v0.1.0 is intended for local testing/demo use, not public internet exposure.

## Roadmap

- v0.2.0: voice with OpenAI
- v0.3.0: Gemini provider exploration
