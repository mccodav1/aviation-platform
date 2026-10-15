#!/bin/sh
set -e

# Schema only - content seeding is the separate, one-time bootstrap_site
# step, so a restart never touches what officers have edited.
python manage.py migrate --noinput

exec "$@"
