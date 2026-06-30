# Release Checklist

Release target: `v0.1.2 - Blanzy Labs Standardization Patch`

## Repo Identity

- [ ] Confirm repo is `blanzy-labs/ai-council`.
- [ ] Confirm display name is AI Council.
- [ ] Confirm README uses Blanzy Labs AI app family positioning.
- [ ] Confirm GitHub description and topics are current.
- [ ] Confirm branch is `main`.

## Documentation

- [ ] README links to `docs/disclaimer.md`.
- [ ] README links to `docs/security-and-privacy.md`.
- [ ] README links to `docs/local-install.md`.
- [ ] README links to `docs/troubleshooting.md`.
- [ ] `LICENSE` exists.
- [ ] Release notes are prepared under `docs/release-notes/`.
- [ ] Validation doc is prepared under `docs/validation/`.

## Git Safety

- [ ] No tag movement.
- [ ] Existing `v0.1.0` and `v0.1.1` tags and releases remain unchanged.
- [ ] `.env` is ignored.
- [ ] `.env` is not tracked.
- [ ] `.env` is not staged.
- [ ] No real secrets, API keys, tokens, credentials, private prompts, or sensitive data are committed.

## Validation

- [ ] Backend tests pass: `cd backend && uv run pytest`.
- [ ] Frontend build passes: `cd frontend && pnpm build`.
- [ ] Docker build passes: `docker compose build`.
- [ ] Docker smoke test passes where practical.
- [ ] Mock provider flow works.
- [ ] OpenAI missing-key behavior is clean.
- [ ] No real OpenAI calls happen in normal tests.

## Security And Privacy

- [ ] Provider keys remain backend-only.
- [ ] Mock provider works without `OPENAI_API_KEY`.
- [ ] No Gemini provider was added.
- [ ] No voice feature was added.
- [ ] No database, persistence, login/auth, telemetry, hosted deployment, token-level streaming, or autonomous agent loop was added.
- [ ] Disclaimer and security/privacy docs warn users about usage, costs, provider data flow, and sensitive data.

## Release

- [ ] Commit message: `Standardize AI Council repo documentation`.
- [ ] Tag: `v0.1.2`.
- [ ] GitHub release title: `v0.1.2 - Blanzy Labs Standardization Patch`.
- [ ] GitHub release notes source: `docs/release-notes/v0.1.2.md`.
