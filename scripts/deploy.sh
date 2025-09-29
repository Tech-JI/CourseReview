#!/bin/sh

set -e

echo $whoami

echo "Starting application deployment inside container..."

echo "Build static files"

echo 'yes' | uv run manage.py collectstatic

# Run Django migrations
echo "[INFO] Running database migrations..."
uv run manage.py migrate

uv run manage.py makemigrations

echo "[INFO] Creating superuser..."
uv run create_admin.py

echo "[INFO] Setting up admin permissions..."
# Execute the Python commands to make the last user an admin
uv run python manage.py shell << 'EOF'
from django.contrib.auth.models import User
u = User.objects.last()
if u:
    u.is_active = True
    u.is_staff = True
    u.is_admin = True
    u.save()
    print(f"User {u.username} has been made an admin.")
else:
    print("No user found to make admin.")
EOF

echo "[INFO] Application deployment completed successfully!"
