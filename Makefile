.PHONY: up down logs api-logs worker-logs web-logs db-shell migrate seed test reset-db ingest-demo

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

api-logs:
	docker compose logs -f api

worker-logs:
	docker compose logs -f worker

web-logs:
	docker compose logs -f web

db-shell:
	docker compose exec db psql -U postgres contentfinder

migrate:
	docker compose exec api alembic upgrade head

seed:
	docker compose exec api python -m scripts.seed

test:
	docker compose exec api pytest tests/ -v

reset-db:
	docker compose down -v && docker compose up -d db

ingest-demo:
	docker compose exec api python -m scripts.ingest_demo
