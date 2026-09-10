#!/bin/sh
set -eu

: "${BACKUP_FILE:?BACKUP_FILE is required}"
: "${BACKUP_AGE_IDENTITY_FILE:?BACKUP_AGE_IDENTITY_FILE is required}"
: "${RESTORE_DATABASE_URL:?RESTORE_DATABASE_URL must target a disposable drill database}"
: "${ALLOW_DESTRUCTIVE_RESTORE_DRILL:?Set ALLOW_DESTRUCTIVE_RESTORE_DRILL=yes for a disposable database}"

if [ "$ALLOW_DESTRUCTIVE_RESTORE_DRILL" != "yes" ]; then
    echo "Restore drill confirmation was not exactly 'yes'." >&2
    exit 2
fi
if [ -n "${PRODUCTION_DATABASE_URL:-}" ] && [ "$RESTORE_DATABASE_URL" = "$PRODUCTION_DATABASE_URL" ]; then
    echo "Refusing to restore over the production database." >&2
    exit 2
fi

sha256sum -c "$BACKUP_FILE.sha256"
age --decrypt --identity "$BACKUP_AGE_IDENTITY_FILE" "$BACKUP_FILE" | pg_restore --clean --if-exists --no-owner --no-acl --dbname "$RESTORE_DATABASE_URL"
psql "$RESTORE_DATABASE_URL" --set=ON_ERROR_STOP=1 --command "SELECT count(*) AS alembic_revision_count FROM alembic_version;"
psql "$RESTORE_DATABASE_URL" --set=ON_ERROR_STOP=1 --command "SELECT count(*) AS user_count FROM users;"
