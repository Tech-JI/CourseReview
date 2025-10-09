#!/bin/sh
set -e
/bin/sh ./scripts/deploy.sh
exec uv run gunicorn website.wsgi:application --bind 0.0.0.0:8000
