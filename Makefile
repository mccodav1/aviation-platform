# bash with pipefail, so a failing command inside a pipe (e.g. pg_dump in
# `make backup`) fails the target instead of leaving a silently empty file.
SHELL := /bin/bash
.SHELLFLAGS := -o pipefail -c

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
# Gets (or re-gets, after changing CERT_DOMAINS) the HTTPS certificate
# for CERT_DOMAINS from Let's Encrypt. Needs DNS pointing here and the
# stack up on port 80 - see "Enabling HTTPS" in docs/DEPLOY.md.
cert:
	docker compose run --rm --entrypoint sh certbot -c '\
		[ -n "$$CERT_DOMAINS" ] && [ -n "$$CERT_EMAIL" ] || { echo "Set CERT_DOMAINS and CERT_EMAIL in .env first." >&2; exit 1; }; \
		certbot certonly --webroot -w /var/www/certbot --cert-name site \
			-d "$$CERT_DOMAINS" --email "$$CERT_EMAIL" \
			--agree-tos --no-eff-email --non-interactive'

compose-seed:
	docker compose exec web python manage.py bootstrap_site

compose-superuser:
	docker compose exec web python manage.py createsuperuser

# Backups: the database plus both upload volumes (media, private_media),
# into backups/<date_time>/ - db.sql.gz and files.tgz. Everything else is
# rebuilt from the repo. Copy backups/ off the server too; a backup on
# the same disk doesn't survive losing the server.
BACKUP_DIR := backups/$(shell date +%Y-%m-%d_%H%M%S)

backup:
	@mkdir -p $(BACKUP_DIR)
	docker compose exec -T db sh -c 'pg_dump --clean --if-exists -U "$$POSTGRES_USER" "$$POSTGRES_DB"' | gzip > $(BACKUP_DIR)/db.sql.gz
	docker compose exec -T web tar czf - -C /data media private_media > $(BACKUP_DIR)/files.tgz
	@echo "Backed up to $(BACKUP_DIR)"

# Replaces the current database and uploads with a backup:
#   make restore BACKUP=backups/2026-10-15_030000
# Asks for confirmation (or pass CONFIRM=yes). Stops the site while it
# restores, then starts it again (which runs any newer migrations).
restore:
	@test -n "$(BACKUP)" || { echo "Usage: make restore BACKUP=backups/<date_time>"; exit 1; }
	@test -f "$(BACKUP)/db.sql.gz" -a -f "$(BACKUP)/files.tgz" || { echo "$(BACKUP) needs db.sql.gz and files.tgz"; exit 1; }
	@if [ "$(CONFIRM)" != "yes" ]; then \
		read -p "This REPLACES the site's current database and uploads with $(BACKUP). Type yes to continue: " answer; \
		[ "$$answer" = "yes" ] || { echo "Cancelled."; exit 1; }; \
	fi
	docker compose stop web
	gunzip -c $(BACKUP)/db.sql.gz | docker compose exec -T db sh -c 'psql -q -v ON_ERROR_STOP=1 --single-transaction -U "$$POSTGRES_USER" "$$POSTGRES_DB"' > /dev/null
	docker compose run --rm --no-deps -T --entrypoint sh web -c 'rm -rf /data/media/* /data/private_media/* && tar xzf - -C /data' < $(BACKUP)/files.tgz
	docker compose start web
	@echo "Restored from $(BACKUP)"

.PHONY: migrate migrations runserver bootstrap test up down nuke logs cert compose-seed compose-superuser backup restore
