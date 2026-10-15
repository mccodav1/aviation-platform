#!/bin/sh
set -e

# Schema only - content seeding is the separate, one-time bootstrap_site
# step, so a restart never touches what officers have edited.
python manage.py migrate --noinput

# Creates the .env superuser on first start; a no-op once it exists.
python manage.py ensure_superuser

exec "$@"
