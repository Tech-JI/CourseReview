.PHONY: run dev-frontend clean collect install-frontend format format-backend format-frontend lint lint-backend lint-frontend makemigrations migrate shell createsuperuser help

# Default target when 'make' is run without arguments
.DEFAULT_GOAL := help

help:
	@echo "Available commands:"
	@echo "  run                   - Starts the Django development server (formats backend code first)"
	@echo "  dev-frontend          - Starts the frontend development server (formats frontend code first)"
	@echo "  clean                 - Clears Django session data"
	@echo "  collect               - Collects Django static files"
	@echo "  install-frontend      - Installs frontend dependencies using bun"
	@echo "  format                - Formats both backend (Python) and frontend (JS/TS/CSS) code"
	@echo "  format-backend        - Formats Python code using isort and black"
	@echo "  format-frontend       - Formats frontend code using prettier"
	@echo "  lint                  - Lints both backend (Python) and frontend (JS/TS/CSS) code"
	@echo "  lint-backend          - Lints Python code using ruff"
	@echo "  lint-frontend         - Lints frontend code using eslint"
	@echo "  makemigrations        - Creates new Django model migrations"
	@echo "  migrate               - Applies Django database migrations"
	@echo "  shell                 - Opens a Django shell"
	@echo "  createsuperuser       - Creates a Django superuser account"

run: format-backend
	@echo "Starting Django development server..."
	uv run manage.py runserver

dev-frontend: format-frontend
	@echo "Starting frontend dev server from frontend/ folder..."
	cd frontend && bun run dev

clean:
	@echo "Clearing Django session data..."
	uv run manage.py clearsession

collect:
	@echo "Collecting Django static files (confirming 'yes')..."
	echo 'yes' | uv run manage.py collectstatic

install-frontend:
	@echo "Installing frontend dependencies with bun..."
	cd frontend && bun install

format: format-backend format-frontend
	@echo "All code formatted successfully!"

format-backend:
	@echo "Formatting backend (Python) code with isort and black..."
	uvx ruff format

format-frontend:
	@echo "Formatting frontend code with prettier..."
	cd frontend && bun run format

lint: lint-backend lint-frontend
	@echo "All code linted successfully!"

lint-backend: format-backend
	@echo "Linting backend (Python) code with ruff..."
	uvx ruff check

lint-frontend: format-frontend
	@echo "Linting frontend code with eslint..."
	cd frontend && bun run lint

makemigrations:
	@echo "Creating Django database migrations..."
	uv run manage.py makemigrations

migrate:
	@echo "Applying Django database migrations..."
	uv run manage.py migrate

shell:
	@echo "Opening Django shell..."
	uv run manage.py shell

createsuperuser:
	@echo "Creating Django superuser account..."
	uv run manage.py createsuperuser
