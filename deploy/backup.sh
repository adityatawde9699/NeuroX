#!/bin/sh
set -eu

: "${DATABASE_URL_FILE:?DATABASE_URL_FILE is required}"
: "${BACKUP_AGE_RECIPIENT:?BACKUP_AGE_RECIPIENT is required}"
: "${BACKUP_DIRECTORY:=/backups}"

case "$BACKUP_DIRECTORY" in
    /|"") echo "BACKUP_DIRECTORY must be a dedicated directory" >&2; exit 2 ;;
esac

database_url=$(tr -d '\r\n' < "$DATABASE_URL_FILE")
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
umask 077
mkdir -p "$BACKUP_DIRECTORY"
output="$BACKUP_DIRECTORY/neurox-$timestamp.dump.age"
pg_dump --format=custom --no-owner --no-acl "$database_url" | age --recipient "$BACKUP_AGE_RECIPIENT" --output "$output"
sha256sum "$output" > "$output.sha256"
find "$BACKUP_DIRECTORY" -type f -name 'neurox-*.dump.age*' -mtime +"${BACKUP_RETENTION_DAYS:-30}" -delete
printf '%s\n' "$output"
