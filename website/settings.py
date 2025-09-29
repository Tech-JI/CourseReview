import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY")
# url and api for wj platform
SIGNUP_QUEST_API_KEY = os.getenv("SIGNUP_QUEST_API_KEY")
SIGNUP_QUEST_URL = os.getenv("SIGNUP_QUEST_URL")
SIGNUP_QUEST_QUESTIONID = os.getenv("SIGNUP_QUEST_QUESTIONID")
LOGIN_QUEST_API_KEY = os.getenv("LOGIN_QUEST_API_KEY")
LOGIN_QUEST_URL = os.getenv("LOGIN_QUEST_URL")
LOGIN_QUEST_QUESTIONID = os.getenv("LOGIN_QUEST_QUESTIONID")
RESET_QUEST_API_KEY = os.getenv("RESET_QUEST_API_KEY")
RESET_QUEST_URL = os.getenv("RESET_QUEST_URL")
RESET_QUEST_QUESTIONID = os.getenv("RESET_QUEST_QUESTIONID")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
print(">>> FRONTEND_URL =", FRONTEND_URL)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Load development config
with open(Path(BASE_DIR) / "development.yaml") as f:
    config = yaml.safe_load(f)

for key, value in config.items():
    globals()[key] = value

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG") == "True"


# Rest Framework

if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOWED_ORIGINS = [
        FRONTEND_URL,
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    ]

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "coursereview"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}


CELERY_BROKER_URL = os.environ["REDIS_URL"]


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/
STATICFILES_DIRS = (os.path.join(BASE_DIR, "static"),)

ROOT_ASSETS_DIR = os.path.join(BASE_DIR, "root_assets")

SESSION_COOKIE_SECURE = not DEBUG

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 100},
        },
        "KEY_PREFIX": "coursereview",
    }
}
