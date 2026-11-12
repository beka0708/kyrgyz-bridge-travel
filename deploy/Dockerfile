# syntax=docker/dockerfile:1
# Build context: repository root (Tailwind scans backend templates while building CSS).

# --- 1. Frontend: Vite + Tailwind -> backend/static/dist ---------------------------
FROM node:22-alpine AS frontend
# Set NPM_REGISTRY=https://registry.npmmirror.com in .env if the official registry is slow.
ARG NPM_REGISTRY=https://registry.npmjs.org/
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
# cache + retries: rebuilds do not re-download, flaky networks do not break the build
RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund --registry="$NPM_REGISTRY" \
    --fetch-retries=5 --fetch-retry-mintimeout=20000
COPY frontend/ ./
COPY backend/templates/ /app/backend/templates/
COPY backend/apps/ /app/backend/apps/
RUN npm run build

# --- 2. Python app ----------------------------------------------------------------
FROM python:3.13-slim AS app
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_HTTP_TIMEOUT=120 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY backend/ ./
COPY --from=frontend /app/backend/static/dist/ ./static/dist/

# Static files are baked into the image; a throwaway key is enough for collectstatic.
RUN SECRET_KEY=build-only DATABASE_URL=sqlite:////tmp/build.db \
    python manage.py collectstatic --noinput -v0

RUN useradd --uid 1000 --create-home app \
    && mkdir -p /app/media /app/var/geoip /tmp/django-cache \
    && chown -R app:app /app/media /app/var /tmp/django-cache
USER app

EXPOSE 8000
ENTRYPOINT ["/app/deploy-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-"]
