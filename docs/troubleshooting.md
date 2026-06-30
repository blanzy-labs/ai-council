# Troubleshooting

## Docker Desktop Not Running

Start Docker Desktop or your Docker daemon, then retry:

```sh
docker compose up --build
```

Check the stack:

```sh
docker compose ps
```

## Ports 8000 Or 5173 Already In Use

AI Council defaults to:

- Backend: `8000`
- Frontend: `5173`

Stop the process using the port, or adjust `BACKEND_PORT` and `FRONTEND_PORT` in `.env`.

## Frontend Cannot Reach Backend

- Confirm backend health: `curl http://localhost:8000/health`.
- Confirm `VITE_API_BASE_URL=http://localhost:8000`.
- Restart the frontend after editing `.env`.
- Use matching local origins: `http://localhost:5173` or `http://127.0.0.1:5173`.

## Backend Health Check Fails

Start the backend locally:

```sh
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then check:

```sh
curl http://localhost:8000/health
curl http://localhost:8000/version
```

## OpenAI Key Missing

Mock mode works without a key. Real OpenAI calls require:

```env
OPENAI_API_KEY=
```

Set the key in `.env` or the backend environment, then restart the backend.

## Mock Provider Works But OpenAI Fails

- Confirm `OPENAI_API_KEY` is set.
- Confirm the selected provider is `openai`.
- Confirm the configured model is available to your OpenAI account.
- Check OpenAI billing, rate limits, and usage limits.
- Review backend logs without printing or sharing secrets.

## Sessions Disappear After Restart

This is expected in v0.1.x. Sessions, transcripts, events, and exportable state are in memory only. Restarting the backend clears runtime state.

## EventSource Activity Panel Not Updating

- Confirm the session was created and a council run or chat is active.
- Check `GET /sessions/{session_id}/events/recent`.
- Check the browser network tab for the EventSource connection.
- Confirm local CORS origin settings match the frontend URL.
- Refresh the page if the browser held a stale EventSource connection.

## pnpm Install Or Build Issues

From `frontend/`:

```sh
pnpm install
pnpm build
```

If the build still fails, confirm the local Node version supports the repo's Vite/TypeScript toolchain, then reinstall dependencies.

## uv Or Python Environment Issues

From `backend/`:

```sh
uv sync
uv run pytest
```

Confirm Python 3.13 is available. The backend package requires Python `>=3.13,<3.14`.

## .env Not Loaded

- Confirm `.env` exists at the repo root.
- Confirm the backend or Docker Compose was restarted after changes.
- Confirm values are not wrapped in shell-specific syntax.
- Do not place provider keys in frontend files.

## Browser Cache Or Stale Frontend

- Hard refresh the browser.
- Restart `pnpm dev`.
- Rebuild the Docker frontend image with `docker compose build frontend`.

## CORS Or Local URL Mismatch

Default allowed frontend origins are:

- `http://localhost:5173`
- `http://127.0.0.1:5173`

If you use a different local URL, add comma-separated origins with `CORS_ORIGINS` and restart the backend.
