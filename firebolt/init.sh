#!/usr/bin/env bash
set -euo pipefail

FIREBOLT_CORE_URL_BASE=${FIREBOLT_CORE_URL:-http://localhost:3473}
DB=${FIREBOLT_DB:-demo_db}
TABLE=${FIREBOLT_TABLE:-demo_events}

run_sql() {
  local sql="$1"
  curl -sS "${FIREBOLT_CORE_URL_BASE}?database=${DB}" --data-binary "$sql" >/dev/null
}

echo "Creating database $DB if not exists..."
# CREATE DATABASE must run without database param
curl -sS "${FIREBOLT_CORE_URL_BASE}" --data-binary "CREATE DATABASE IF NOT EXISTS \"$DB\";" >/dev/null

echo "Creating table $DB.$TABLE if not exists..."
run_sql "CREATE TABLE IF NOT EXISTS \"$TABLE\" (\n  event_id INT,\n  user_id INT,\n  event_type TEXT,\n  event_ts TEXT,\n  payload TEXT\n);"

echo "Done."
