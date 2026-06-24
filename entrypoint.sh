#!/bin/sh
set -e

# Wait until PostgreSQL is accepting connections.
# Uses Django's own resolved DB config, so it works with either DATABASE_URL
# or the individual DB_* variables.
echo "Waiting for database ..."
python <<'PYCODE'
import os, time
import django
from django.db import connections
from django.db.utils import OperationalError

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

for attempt in range(60):
    try:
        connections["default"].ensure_connection()
        print("Database is up.")
        break
    except OperationalError:
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
