#!/bin/sh
# Container start: apply migrations, then run the given command (gunicorn by default).
set -e
if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  python manage.py migrate --noinput
  # visitor countries: download the database once; without it countries are «unknown»
  python manage.py update_geoip --if-missing || echo "GeoIP download failed, will retry by cron"
fi
exec "$@"
