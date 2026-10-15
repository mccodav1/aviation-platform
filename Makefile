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

# One-time content seed (see bootstrap_site) - same as compose-seed.
bootstrap: migrate
	$(DEV) bootstrap_site

test:
	$(DEV) test

# Production-style stack: nginx -> gunicorn -> Postgres (see compose.yaml).
up:
	docker compose up -d --build

down:
	docker compose down

# Start over from nothing: also deletes the volumes (database, media,
# private_media) and every image the stack uses. Follow with
# `make up` and `make compose-seed`.
nuke:
	docker compose down -v --rmi all

logs:
	docker compose logs -f

# One-time content seed for a fresh deployment (see bootstrap_site).
compose-seed:
	docker compose exec web python manage.py bootstrap_site

compose-superuser:
	docker compose exec web python manage.py createsuperuser

.PHONY: migrate migrations runserver bootstrap test up down nuke logs compose-seed compose-superuser
