# Create a debug version of init.sh
#!/usr/bin/env bash
set -euo pipefail

FIREBOLT_CORE_URL_BASE=${FIREBOLT_CORE_URL:-http://localhost:3473}
DB=${FIREBOLT_DB:-demo_db}
TABLE=${FIREBOLT_TABLE:-demo_events}

run_sql() {
  local sql="$1"
  echo "Executing: $sql"
  curl -sS "${FIREBOLT_CORE_URL_BASE}?database=${DB}" --data-binary "$sql"
  echo ""
}

echo "Creating database $DB if not exists..."
echo "Executing: CREATE DATABASE IF NOT EXISTS \"$DB\";"
curl -sS "${FIREBOLT_CORE_URL_BASE}" --data-binary "CREATE DATABASE IF NOT EXISTS \"$DB\";"
echo ""

echo "Creating table $DB.$TABLE if not exists..."
# Fixed SQL without \n characters and with PRIMARY INDEX
run_sql "CREATE TABLE IF NOT EXISTS \"$TABLE\" (
  event_id INT,
  user_id INT,
  event_type TEXT,
  event_ts TEXT,
  payload TEXT
) PRIMARY INDEX event_id;"

echo "Verifying table creation..."
run_sql "SHOW TABLES;"

echo "Done."
EOF

# Make it executable
chmod +x firebolt/init.sh

# Run the debug version
bash firebolt/init.sh
