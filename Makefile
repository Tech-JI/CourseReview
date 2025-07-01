.PHONY: run clean collect format format-backend format-frontend makemigrations migrate shell createsuperuser dev-frontend help

# Default target when 'make' is run without arguments
.DEFAULT_GOAL := help

help:
	@echo "Available commands:"
	@echo "  run                   - Starts the Django development server (formats backend code first)"
	@echo "  dev-frontend          - Starts the frontend development server (formats frontend code first)"
	@echo "  clean                 - Clears Django session data"
	@echo "  collect               - Collects Django static files"
	@echo "  format                - Formats both backend (Python) and frontend (JS/TS/CSS) code"
	@echo "  format-backend        - Formats Python code using isort and black"
	@echo "  format-frontend       - Formats frontend code using prettier"
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

format: format-backend format-frontend
	@echo "All code formatted successfully!"

format-backend:
	@echo "Formatting backend (Python) code with isort and black..."
	uvx isort .
	uvx black .

format-frontend:
	@echo "Formatting frontend code with prettier..."
	cd frontend && bunx prettier . -w

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
