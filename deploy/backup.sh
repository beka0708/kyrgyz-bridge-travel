#!/bin/sh
# Daily backup of the database and uploaded photos; keeps the last 7 days.
# Cron (on the server, as the deploy user):
#   30 3 * * * /opt/kg-tours/deploy/backup.sh >> /opt/kg-tours/backups/backup.log 2>&1
set -eu
cd "$(dirname "$0")"
COMPOSE="docker compose -f compose.prod.yml --env-file ${ENV_FILE:-../.env}"
DEST="${BACKUP_DIR:-../backups}"
STAMP="$(date +%Y-%m-%d_%H%M)"
mkdir -p "$DEST"

$COMPOSE exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$DEST/db-$STAMP.dump"
# Originals only: WebP variants in media/cache are rebuilt by `manage.py warm_images`.
$COMPOSE exec -T app tar -C /app/media --exclude=./cache -czf - . > "$DEST/media-$STAMP.tar.gz"

find "$DEST" -name 'db-*.dump' -mtime +7 -delete
find "$DEST" -name 'media-*.tar.gz' -mtime +7 -delete
echo "$(date -Iseconds) backup ok: db-$STAMP.dump media-$STAMP.tar.gz"
# Off-site copy (recommended): e.g. rclone copy "$DEST" remote:kg-tours-backups
