#!/bin/sh
# Container start: apply migrations, then run the given command (gunicorn by default).
set -e
if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  python manage.py migrate --noinput
fi
exec "$@"
