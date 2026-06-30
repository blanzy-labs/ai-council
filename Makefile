.PHONY: test-backend build-frontend test docker-up docker-build docker-down

test-backend:
	cd backend && uv run pytest

build-frontend:
	cd frontend && pnpm build

test: test-backend build-frontend

docker-up:
	docker compose up --build

docker-build:
	docker compose build

docker-down:
	docker compose down
