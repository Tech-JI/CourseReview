# Config

Use YAML and environment variables for robust and secure configuration. All the customizable fields can be specified in `config.yaml` and environment variables (or `.env` file at local dev).

## TL;DR

1. Copy `.env.example` file to `.env`, fill in:
   - `SECRET_KEY`
   - `TURNSTILE_SECRET_KEY`
   - `QUEST__SIGNUP__API_KEY`
   - `QUEST__LOGIN__API_KEY`
   - `QUEST__RESET__API_KEY`
   - (If in production) `DATABASE__URL` and `REDIS__URL`
2. Copy `config.yaml.example` to `config.yaml`, fill in:
   - `DEBUG`: `true` if at dev, `false` if in production
   - `URL` and `QUESTIONID` in all actions in `QUEST`
   - (If in production) backend domains in `ALLOWED_HOSTS`, frontend domains in `CORS_ALLOWED_ORIGINS`
3. That's it!

## Priority

env > `config.yaml` > default config

Every field (including nested ones) can be specified anywhere (i.e. env, `config.yaml`, none/default), and config will be loaded with each field following the above priority order.

### Environment Variables

- Environment variables are used to set secrets and credentials.
- Use `.env` file for local development. Directly export environment variables at production.
- Copy this `.env.example` file to `.env` and fill in the secrets for local development.
- `.env` should **NOT** be committed (already git ignored).
- Use `PARENT__CHILD` format to override nested settings. `__` means parental relationship.
- Use `,` as delimiter for lists.

```env path=.env
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
DATABASE__URL=postgres://admin:test@127.0.0.1:5432/coursereview
REDIS__URL=redis://localhost:6379/0

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

QUEST__RESET__API_KEY=dummy3
# QUEST__RESET__URL=
# QUEST__RESET__QUESTIONID=

# --- Other Overrides (Optional) ---
# Example of overriding a nested value in the AUTH dictionary
# AUTH__OTP_TIMEOUT=60

# Example of overriding a list with a comma-separated string
# ALLOWED_HOSTS=localhost,127.0.0.1,dev.my-app.com
```

### YAML

- `config.yaml` is used to set custom but not secret configs (e.g. frontend and backend URLs, questionnaire ID)
- Copy this `config.yaml.example` file to `config.yaml` and fill in the required fields.
- `config.yaml` should **NOT** be committed (already git ignored).

```yaml path=config.yaml
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
# AUTH:
#   OTP_TIMEOUT: 120
#   TEMP_TOKEN_TIMEOUT: 600
#   TOKEN_RATE_LIMIT: 5
#   TOKEN_RATE_LIMIT_TIME: 600
#   PASSWORD_LENGTH_MIN: 10
#   PASSWORD_LENGTH_MAX: 32
#   EMAIL_DOMAIN_NAME: "sjtu.edu.cn"
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
  RESET:
    # API_KEY: Use env
    URL: "https://wj.sjtu.edu.cn/q/dummy2"
    QUESTIONID: 10000002
# AUTO_IMPORT_CRAWLED_DATA: true
```

### Default Config

- Just for example.
- `settings.py` should **NOT** be modified by non-developers.
- The fields whose default values are `None` are mandatory, either in env or in `config.yaml`.

```python path=website/settings.py
# --- Default Configuration ---
DEFAULTS = {
    "DEBUG": True,
    "SECRET_KEY": None,
    "ALLOWED_HOSTS": ["127.0.0.1", "localhost"],
    "CORS_ALLOWED_ORIGINS": ["http://localhost:5173", "http://127.0.0.1:5173"],
    "SESSION": {
        "COOKIE_AGE": 2592000,  # 30 days
        "SAVE_EVERY_REQUEST": True,
    },
    "AUTH": {
        "OTP_TIMEOUT": 120,
        "TEMP_TOKEN_TIMEOUT": 600,
        "TOKEN_RATE_LIMIT": 5,
        "TOKEN_RATE_LIMIT_TIME": 600,
        "PASSWORD_LENGTH_MIN": 10,
        "PASSWORD_LENGTH_MAX": 32,
        "EMAIL_DOMAIN_NAME": "sjtu.edu.cn",
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
        "RESET": {
            "API_KEY": None,
            "URL": None,
            "QUESTIONID": None,
        },
    },
    "AUTO_IMPORT_CRAWLED_DATA": True,
}
```
