#!/bin/bash

# Redirect all output to both stdout and a log file for debugging
exec > >(tee -a dev_setup.log) 2>&1

set -e

echo "Setting up the development environment..."

# Step 1-4: Create virtual environment, install dependencies, setup pre-commit hooks
echo "[INFO] Creating virtual environment..."
uv venv .venv
source .venv/bin/activate
echo "[INFO] Installing dependencies..."
uv sync
echo "[INFO] Setting up pre-commit hooks..."
uv run pre-commit install

# Step 6: Make directory for builds of static files
echo "[INFO] Creating static files directory..."
mkdir -p staticfiles

# Step 7: Create .env file for storing secrets
echo "[INFO] Creating .env file..."
cat > .env << 'EOL'
   # PostgreSQL
   DB_USER=admin
   DB_PASSWORD=test
   DB_HOST=localhost
   DB_PORT=5432
   REDIS_URL=redis://localhost:6379/0
   SECRET_KEY=02247f40-a769-4c49-9178-4c038048e7ad
   DEBUG=True
   OFFERINGS_THRESHOLD_FOR_TERM_UPDATE=100
EOL

# Step 8: Build static files
echo "[INFO] Building static files..."
make collect

# Step 9: Configure database using Docker with lightweight images
echo "[INFO] Starting PostgreSQL container..."
# Stop and remove any existing container with the same name
docker stop coursereview-postgres 2>/dev/null || true
docker rm coursereview-postgres 2>/dev/null || true

docker run -d --name coursereview-postgres -p 5432:5432 \
  -e POSTGRES_DB=coursereview \
  -e POSTGRES_USER=admin \
  -e POSTGRES_PASSWORD=test \
  --restart unless-stopped \
  postgres:16-alpine

# Wait for PostgreSQL to be ready
echo "[INFO] Waiting for PostgreSQL to be ready..."
sleep 15

# Check if PostgreSQL container is running
if docker ps | grep coursereview-postgres > /dev/null; then
    echo "[INFO] PostgreSQL container is running"
else
    echo "[ERROR] PostgreSQL container failed to start"
    exit 1
fi

# Step 10: Run valkey using docker with a lightweight image
echo "[INFO] Starting Valkey container..."
# Stop and remove any existing container with the same name
docker stop valkey-cache 2>/dev/null || true
docker rm valkey-cache 2>/dev/null || true

docker run -d --name valkey-cache -p 6379:6379 \
  --restart unless-stopped \
  valkey/valkey:7-alpine

# Wait for Valkey to be ready
echo "[INFO] Waiting for Valkey to be ready..."
sleep 8

# Check if Valkey container is running
if docker ps | grep valkey-cache > /dev/null; then
    echo "[INFO] Valkey container is running"
else
    echo "[ERROR] Valkey container failed to start"
    exit 1
fi

# Step 9 continued: Auto setup database connection and static file routes in Django
echo "[INFO] Running Django migrations and creating database tables..."
make migrate

# Step 12: Add local admin
echo "[INFO] Creating superuser..."
make createsuperuser

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
else
    print("No user found to make admin.")
EOF

echo "[INFO] Development environment setup complete!"
echo "PostgreSQL and Valkey are running in Docker containers."
echo "You can now run 'make run' to start the development server."
echo "[INFO] Log saved to dev_setup.log"