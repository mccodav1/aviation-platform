# Aviation Platform

Django site for the Salinas Pilots Association (SPA). Site content (hero
images, nav, cards, info panels) is data-driven through the Django admin
rather than hardcoded in templates, with the goal of eventually reusing this
codebase as a template for other flying clubs (each on its own deployment).

## Local development (runserver + SQLite)

```
uv sync
make bootstrap   # migrate + bootstrap_site (seed content and images)
make runserver
```

`db.sqlite3`, `media/` and `private_media/` aren't committed. `make bootstrap`
rebuilds them from `base_images/` and `base_documents/` (tracked seed files)
and the fixture in `core/fixtures/`. The
Makefile turns `DJANGO_DEBUG` on for these targets, so no `.env` is needed.

## Production-style (compose: nginx + gunicorn + Postgres)

### Files

- **`compose.yaml`** defines three services:
  - `db`: Postgres 17. Its data lives in the `pgdata` volume.
  - `web`: Django under gunicorn, built from this repo's `Dockerfile`.
    It runs `migrate` on every start (`docker/entrypoint.sh`). Uploads
    live in the `media` and `private_media` volumes.
  - `nginx`: listens on host port 80 (`HTTP_PORT`), serves `/media/`
    straight off the `media` volume, and proxies everything else to `web`.
    It never mounts `private_media`; those files only go out through
    Django's permission-checked views.
- **`.env.example`** is the template for every setting, split into
  MANDATORY (compose refuses to start without them) and OPTIONAL
  (defaults shown, commented out).
- **`.env`** is your copy with real values. It isn't committed. Compose
  reads it for both `db` and `web`, and `make runserver` reads it too.
  Compose fixes `POSTGRES_HOST` and `DATA_DIR` itself, so the same `.env`
  still runs local `runserver` against SQLite.
- **`Dockerfile`** bakes the whole repo into the image, including the
  seed sources (`base_images/`, `base_documents/`, `core/fixtures/`).
  `.dockerignore` keeps local `db.sqlite3`, `media/` and `private_media/`
  out of the image.

### Starting from scratch

```
cp .env.example .env     # then fill in the MANDATORY section
make up                  # build the image and start db, web, nginx
make compose-seed        # one-time content load (bootstrap_site)
```

On start, `web` runs `migrate` and then `ensure_superuser`, which creates
the admin account from `DJANGO_SUPERUSER_USERNAME` /
`DJANGO_SUPERUSER_PASSWORD` if it doesn't exist yet. An existing account
is left alone, so changing the password in `.env` later has no effect -
change it in the admin instead.

The site is then at http://localhost/, and the admin at http://localhost/admin/.

`make compose-seed` copies the seed images and documents into the
volumes and loads `core/fixtures/spa_demo.json` into Postgres. It reads
the copies baked into the image, not your working directory, so after
changing seed data run `make up` again before seeding. It refuses to run
once content exists, so it can't overwrite edits made through the site
(`bootstrap_site --force` overrides that).

For any additional admin accounts, `make compose-superuser` runs
`createsuperuser`. It prompts interactively, so it fails without a TTY.
To create the user without prompts:

```
docker compose exec -e DJANGO_SUPERUSER_PASSWORD='...' web \
    python manage.py createsuperuser --noinput --username another-admin --email you@example.com
```

### Everyday commands

```
make up      # (re)build and start; also how code changes get deployed
make logs    # follow logs from all services
make down    # stop and remove containers - data in the volumes is kept
```

### Wiping everything and starting fresh

```
make nuke    # docker compose down -v --rmi all
```

This deletes the volumes (database, media, private_media) and every
image the stack uses, with no confirmation. Then follow
[Starting from scratch](#starting-from-scratch) from `make up` (your
`.env` is untouched).

See [docs/DEPLOY.md](docs/DEPLOY.md) for deploying to a server, updates,
backups, and the invariants to preserve.
