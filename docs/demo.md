# AI Council Demo Guide

## What AI Council Demonstrates

AI Council v0.1.0 demonstrates a local-first, text-based multi-persona council room with structured council runs, follow-up chat, live activity events, and Markdown/JSON transcript export.

The demo is designed to work with the mock provider, so it does not require an OpenAI API key.

## Recommended Demo Setup

- Use Docker Compose for the cleanest local demo.
- Keep the provider set to `mock` for predictable output.
- Use a fresh browser window at http://localhost:5173.
- Keep a terminal visible for `docker compose up --build` if recording the setup.

Start the app:

```sh
docker compose up --build
```

Stop the app:

```sh
docker compose down
```

## Recommended Demo Flow

1. Start Docker Compose.
2. Open the frontend at http://localhost:5173.
3. Create a session.
4. Run council using mock provider.
5. Send follow-up to whole council.
6. Send follow-up to one persona.
7. Watch live activity events.
8. Export Markdown.
9. Export JSON.

## Suggested Demo Topic

**Title:** Local-first v0.1.0 release council

**Topic:** Should AI Council remain local-first for v0.1.0, or should it add persistence earlier?

**Mode:** `ask_council`

**Personas:** `moderator`, `strategist`, `skeptic`, `builder`, `customer_advocate`

## Suggested Follow-Up Prompts

- What is the riskiest assumption in this plan?
- Builder, what is the smallest useful next improvement?
- Skeptic, what would make this unreliable for testers?
- Customer Advocate, would a non-technical user understand this?

## Optional OpenAI Demo Flow

Only use this if `OPENAI_API_KEY` is configured in the backend environment.

1. Create a session.
2. Select `openai` as provider override.
3. Run a short one-round council.
4. Ask one focused follow-up.
5. Export the transcript.

If no key is configured, OpenAI calls should fail gracefully and mock mode should continue to work.

## Notes For Screen Recording Or Screenshots

- Start with the header visible so the v0.1.0 scope badges are clear.
- Show the health panel before creating a session.
- Use mock provider for deterministic output.
- Show live activity while a run/chat completes.
- Capture the transcript and export panel after generating Markdown.
- Avoid showing `.env`, terminal history containing secrets, or real API keys.

## Known Demo Limitations

- In-memory only
- Event-level streaming only
- No voice
- No Gemini
- No login/auth
- Not hardened for public internet exposure
