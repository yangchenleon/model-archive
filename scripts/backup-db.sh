#!/usr/bin/env bash
# Dump the PostgreSQL volume into backups/ so the database is never the only copy.
# Run from anywhere; the dump is written next to the repository root.
set -euo pipefail
cd "$(dirname "$0")/.."
timestamp=$(date +%Y%m%d-%H%M%S)
mkdir -p backups
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' | gzip > "backups/model-archive-${timestamp}.sql.gz"
echo "backup written: backups/model-archive-${timestamp}.sql.gz"
