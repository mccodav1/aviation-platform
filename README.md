# Aviation Platform

Django site for the Salinas Pilots Association (SPA). Site content (hero
images, nav, cards, info panels) is data-driven through the Django admin
rather than hardcoded in templates, with the goal of eventually reusing this
codebase as a template for other flying clubs (each on its own deployment).

## Local development (runserver + SQLite)

```
uv sync
make bootstrap   # migrate + seed_media + loaddata (demo content/images)
make runserver
```

`db.sqlite3`, `media/` and `private_media/` aren't committed. `make bootstrap`
rebuilds them from `base_images/` and `base_documents/` (tracked seed files)
and the fixtures under `core/fixtures/` and `meetings/fixtures/`. The
Makefile turns `DJANGO_DEBUG` on for these targets, so no `.env` is needed.

## Production-style (compose: nginx + gunicorn + Postgres)

```
cp .env.example .env   # fill in the MANDATORY section
make up
make compose-superuser
make compose-seed      # optional one-time content load
```

The same `.env` also works for `make runserver`, which still uses SQLite.
See [docs/DEPLOY.md](docs/DEPLOY.md) for deploying, updating, backups, and
the invariants to preserve.
