#!/bin/sh
set -e
/bin/sh ./scripts/deploy.sh
exec uv run manage.py runserver  0.0.0.0:8000
