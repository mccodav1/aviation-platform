# Local development: SQLite + runserver, with DEBUG on. Set here rather
# than in .env, so the same .env can drive compose without DEBUG.
DEV = DJANGO_DEBUG=true uv run manage.py

migrate:
	$(DEV) migrate

migrations:
	$(DEV) makemigrations

runserver:
	$(DEV) check_links
	$(DEV) runserver

seed-media:
	$(DEV) seed_media

load-demo:
	$(DEV) loaddata core/fixtures/spa_demo.json

bootstrap: migrate seed-media load-demo

reset: migrations migrate runserver

test:
	$(DEV) test

# Production-style stack: nginx -> gunicorn -> Postgres (see compose.yaml).
up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

# One-time content seed for a fresh deployment (see bootstrap_site).
compose-seed:
	docker compose exec web python manage.py bootstrap_site

compose-superuser:
	docker compose exec web python manage.py createsuperuser

.PHONY: migrate migrations runserver seed-media load-demo bootstrap reset test up down logs compose-seed compose-superuser
