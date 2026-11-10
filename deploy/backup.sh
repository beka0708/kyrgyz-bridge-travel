#!/bin/sh
# Backup of the database and uploaded photos.
#   backup.sh          daily copy, the last 7 days are kept       (backups/)
#   backup.sh monthly  monthly copy, the last 12 months are kept  (backups/monthly/)
# Cron (on the server, as the deploy user) — see deploy/crontab.example.
set -eu
cd "$(dirname "$0")"
COMPOSE="docker compose -f compose.prod.yml --env-file ${ENV_FILE:-../.env}"
ROOT="${BACKUP_DIR:-../backups}"
MODE="${1:-daily}"
if [ "$MODE" = "monthly" ]; then
  DEST="$ROOT/monthly"; KEEP_DAYS=370
else
  DEST="$ROOT"; KEEP_DAYS=7
fi
STAMP="$(date +%Y-%m-%d_%H%M)"
mkdir -p "$DEST"

$COMPOSE exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$DEST/db-$STAMP.dump"
# Originals only: WebP variants in media/cache are rebuilt by `manage.py warm_images`.
$COMPOSE exec -T app tar -C /app/media --exclude=./cache -czf - . > "$DEST/media-$STAMP.tar.gz"

# -maxdepth 1: the daily clean-up must not touch backups/monthly/
find "$DEST" -maxdepth 1 -name 'db-*.dump' -mtime +"$KEEP_DAYS" -delete
find "$DEST" -maxdepth 1 -name 'media-*.tar.gz' -mtime +"$KEEP_DAYS" -delete
echo "$(date -Iseconds) $MODE backup ok: db-$STAMP.dump media-$STAMP.tar.gz"
