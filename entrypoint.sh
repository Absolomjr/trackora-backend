#!/bin/sh
set -e

# Wait until PostgreSQL is accepting connections.
echo "Waiting for database at ${DB_HOST:-db}:${DB_PORT:-5432} ..."
python <<'PYCODE'
import os, socket, time

host = os.getenv("DB_HOST", "db")
port = int(os.getenv("DB_PORT", "5432"))

for attempt in range(60):
    try:
        with socket.create_connection((host, port), timeout=2):
            print("Database is up.")
            break
    except OSError:
        time.sleep(1)
else:
    raise SystemExit("Database not reachable after 60s")
PYCODE

# Apply migrations and collect static assets.
echo "Running migrations ..."
python manage.py migrate --noinput

echo "Collecting static files ..."
python manage.py collectstatic --noinput

# Hand off to the container's main process (gunicorn by default).
exec "$@"
