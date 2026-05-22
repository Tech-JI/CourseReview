# Config

CourseReview uses three configuration sources, merged in this order:

```text
environment variables > config.yaml > built-in defaults
```

Use:

- environment variables for secrets and credentials
- `config.yaml` for non-secret, environment-specific settings
- built-in defaults for sane local defaults

For local development, copy:

- `.env.example` to `.env`
- `config.yaml.example` to `config.yaml`

Neither file should be committed.

## Quick start

1. Copy `.env.example` to `.env`
2. Copy `config.yaml.example` to `config.yaml`
3. Fill in required values
4. Run the app with `python run.py dev`

## Required values

### Usually set in `.env`

These are typically secrets:

- `SECRET_KEY`
- `TURNSTILE_SECRET_KEY`
- `QUEST__SIGNUP__API_KEY`
- `QUEST__LOGIN__API_KEY`
- `QUEST__RESET_PASSWORD__API_KEY`

Infrastructure URLs are also commonly set in `.env`:

- `DATABASE__URL`
- `REDIS__URL`

### Usually set in `config.yaml`

These are typically non-secret and environment-specific:

- `DEBUG`
- `ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`
- `QUEST.SIGNUP.URL`
- `QUEST.SIGNUP.QUESTIONID`
- `QUEST.LOGIN.URL`
- `QUEST.LOGIN.QUESTIONID`
- `QUEST.RESET_PASSWORD.URL`
- `QUEST.RESET_PASSWORD.QUESTIONID`

## Environment variables

Environment variables use `__` to represent nesting.

Examples:

```env
DATABASE__URL=postgres://admin:test@db:5432/coursereview
REDIS__URL=redis://cache:6379/0
AUTH__OTP_TIMEOUT=60
WEB__COURSE__PAGE_SIZE=5
QUEST__RESET_PASSWORD__QUESTIONID=10000002
```

Lists can be overridden with comma-separated strings:

```env
ALLOWED_HOSTS=localhost,127.0.0.1,api.example.com
```

### Local development note

Keep the URLs in `.env` container-friendly:

```env
DATABASE__URL=postgres://admin:test@db:5432/coursereview
REDIS__URL=redis://cache:6379/0
```

This is intentional.

- Podman Compose needs `db` and `cache`
- host-side commands such as `python run.py dev`, `python run.py django ...`, and `python run.py test` automatically rewrite them to `127.0.0.1`

So do **not** change `.env` to `localhost` just for host-side development.

## `.env.example`

```env
# .env.example
# Copy this file to .env and fill in the secrets for local development.
# DO NOT COMMIT .env TO VERSION CONTROL.
# This file overrides config.yaml

# --- Core Security (REQUIRED IN PRODUCTION) ---
# Generate a new one for production!
SECRET_KEY=django-insecure-my-local-dev-secret-key

# --- Local Overrides ---
# Set to False in production
# DEBUG=True

# --- Infrastructure (REQUIRED) ---
# Use a single URL for database and Redis connections.
# Format: driver://user:password@host:port/dbname
DATABASE__URL=postgres://admin:test@db:5432/coursereview
REDIS__URL=redis://cache:6379/0

# --- External Services Secrets (REQUIRED) ---
TURNSTILE_SECRET_KEY=dummy0

# Use PARENT__CHILD format to override nested settings
# URL and ID may be specified in config.yaml
QUEST__SIGNUP__API_KEY=dummy1
# QUEST__SIGNUP__URL=
# QUEST__SIGNUP__QUESTIONID=

QUEST__LOGIN__API_KEY=dummy2
# QUEST__LOGIN__URL=
# QUEST__LOGIN__QUESTIONID=

QUEST__RESET_PASSWORD__API_KEY=dummy3
# QUEST__RESET_PASSWORD__URL=
# QUEST__RESET_PASSWORD__QUESTIONID=

# --- Other Overrides (Optional) ---
# Example of overriding a nested value in the AUTH dictionary
# AUTH__OTP_TIMEOUT=60
# Example of overriding web size constraints
# WEB__COURSE__PAGE_SIZE=5
# WEB__REVIEW__PAGE_SIZE=10
# WEB__REVIEW__COMMENT_MIN_LENGTH=30

# Example of overriding a list with a comma-separated string
# ALLOWED_HOSTS=localhost,127.0.0.1,dev.my-app.com
```

## `config.yaml.example`

```yaml
# Please copy this file to config.yaml and fill in
# corresponding fields.
# For non-secret, environment-specific configuration.
# Values here will override DEFAULTS in settings.py.
# Environment variables will override values here.

DEBUG: true

# SECRET_KEY: Use env

ALLOWED_HOSTS:
  # - "backend.redacted.com"
  - "localhost"
  - "127.0.0.1"

CORS_ALLOWED_ORIGINS:
  # - "https://frontend.redacted.com"
  - "http://localhost:5173"
  - "http://127.0.0.1:5173"

# SESSION:
#   COOKIE_AGE: 2592000 # 30 days
#   SAVE_EVERY_REQUEST: true
#
# WEB:
#   COURSE:
#     PAGE_SIZE: 5
#   REVIEW:
#     PAGE_SIZE: 10
#     COMMENT_MIN_LENGTH: 30
#
# AUTH:
#   OTP_TIMEOUT: 120
#   TEMP_TOKEN_TIMEOUT: 600
#   TOKEN_RATE_LIMIT: 5
#   TOKEN_RATE_LIMIT_TIME: 600
#   PASSWORD_LENGTH_MIN: 10
#   PASSWORD_LENGTH_MAX: 32
#   EMAIL_DOMAIN_NAME: "sjtu.edu.cn"
#   ACTION_LIST:
#     - "signup"
#     - "login"
#     - "reset_password"
#
# DATABASE:
#   URL: Use env
#
# REDIS:
#   URL: Use env
#   MAX_CONNECTIONS: 100
#
# TURNSTILE_SECRET_KEY: Use env

QUEST:
  # BASE_URL: "https://wj.sjtu.edu.cn/api/v1/public/export"
  SIGNUP:
    # API_KEY: Use env
    URL: "https://wj.sjtu.edu.cn/q/dummy0"
    QUESTIONID: 10000000
  LOGIN:
    # API_KEY: Use env
    URL: "https://wj.sjtu.edu.cn/q/dummy1"
    QUESTIONID: 10000001
  RESET_PASSWORD:
    # API_KEY: Use env
    URL: "https://wj.sjtu.edu.cn/q/dummy2"
    QUESTIONID: 10000002

# AUTO_IMPORT_CRAWLED_DATA: true
```

## Built-in defaults

Current built-in defaults are:

```python
DEFAULTS = {
    "DEBUG": True,
    "SECRET_KEY": None,
    "ALLOWED_HOSTS": ["127.0.0.1", "localhost"],
    "CORS_ALLOWED_ORIGINS": ["http://localhost:5173", "http://127.0.0.1:5173"],
    "SESSION": {
        "COOKIE_AGE": 2592000,  # 30 days
        "SAVE_EVERY_REQUEST": True,
    },
    "WEB": {
        "COURSE": {"PAGE_SIZE": 10},
        "REVIEW": {"PAGE_SIZE": 10, "COMMENT_MIN_LENGTH": 30},
    },
    "AUTH": {
        "OTP_TIMEOUT": 120,
        "TEMP_TOKEN_TIMEOUT": 600,
        "TOKEN_RATE_LIMIT": 5,
        "TOKEN_RATE_LIMIT_TIME": 600,
        "PASSWORD_LENGTH_MIN": 10,
        "PASSWORD_LENGTH_MAX": 32,
        "EMAIL_DOMAIN_NAME": "sjtu.edu.cn",
        "ACTION_LIST": ["signup", "login", "reset_password"],
    },
    "DATABASE": {"URL": "sqlite:///db.sqlite3"},
    "REDIS": {"URL": "redis://localhost:6379/0", "MAX_CONNECTIONS": 100},
    "TURNSTILE_SECRET_KEY": None,
    "QUEST": {
        "BASE_URL": "https://wj.sjtu.edu.cn/api/v1/public/export",
        "SIGNUP": {
            "API_KEY": None,
            "URL": None,
            "QUESTIONID": None,
        },
        "LOGIN": {
            "API_KEY": None,
            "URL": None,
            "QUESTIONID": None,
        },
        "RESET_PASSWORD": {
            "API_KEY": None,
            "URL": None,
            "QUESTIONID": None,
        },
    },
    "AUTO_IMPORT_CRAWLED_DATA": True,
}
```

## Production notes

For production, usually:

- set `DEBUG: false`
- set real backend domains in `ALLOWED_HOSTS`
- set real frontend domains in `CORS_ALLOWED_ORIGINS`
- use a strong `SECRET_KEY`
- use real Postgres and Valkey URLs
- keep secrets in environment variables, not in `config.yaml`

Typical production split:

- `/etc/coursereview/secrets.env` for secrets
- `/etc/coursereview/config.yaml` for non-secret config
