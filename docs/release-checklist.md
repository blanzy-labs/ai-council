# Release Checklist

Use this before publishing AI Council v0.1.0.

## Preflight

- [ ] Confirm clean git status: `git status`
- [ ] Review `.env.example`
- [ ] Confirm `.env` is ignored: `git check-ignore .env`
- [ ] Confirm no secrets are committed: `git ls-files | grep -E '(^|/)\\.env$|secret'`
- [ ] Confirm version references are v0.1.0.
- [ ] Review README.
- [ ] Review release notes.

## Validation

- [ ] Run backend tests: `cd backend && uv run pytest`
- [ ] Run frontend build: `cd frontend && pnpm build`
- [ ] Run Docker Compose build: `docker compose build`
- [ ] Run Docker Compose stack: `docker compose up --build`
- [ ] Validate mock provider flow.
- [ ] Validate OpenAI provider manually if key is available.
- [ ] Confirm no real OpenAI calls happen in normal tests.

## Suggested Git Commands

Do not run these automatically.

```sh
git status
git add .
git commit -m "Prepare ai-council v0.1.0 release"
git tag v0.1.0
git push origin main
git push origin v0.1.0
```

## Suggested GitHub Release Command

Do not run this automatically.

```sh
gh release create v0.1.0 \
  --title "v0.1.0 - Local Council MVP" \
  --notes-file docs/release-notes/v0.1.0.md
```
