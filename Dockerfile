FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Dependencies first, so code-only changes reuse this layer on rebuild.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

# Includes base_images/, base_documents/ and the fixtures, so a fresh
# deployment can be seeded from inside the container (bootstrap_site).
COPY . .

# staticfiles/ is a build artifact - WhiteNoise's manifest storage needs
# it generated before any page renders. The secret/hosts here exist only
# so settings will import; nothing is served from this build step.
RUN DJANGO_SECRET_KEY=collectstatic-only DJANGO_ALLOWED_HOSTS=build \
    python manage.py collectstatic --noinput

# The volume mount points are created (and owned) here so that compose's
# named volumes inherit app ownership the first time they're created.
RUN useradd --uid 1000 --no-create-home app \
    && mkdir -p /data/media /data/private_media \
    && chown -R app:app /data
USER app
ENV DATA_DIR=/data

EXPOSE 8000
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--config", "docker/gunicorn.conf.py"]
