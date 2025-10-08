from pathlib import Path
import dj_database_url
from dotenv import load_dotenv
from .config import Config


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_ROOT = BASE_DIR / 'staticfiles'
load_dotenv(BASE_DIR / ".env")

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

config = Config(config_path=BASE_DIR / "config.yaml", defaults=DEFAULTS)


# ==============================================================================
#  MANAGED SETTINGS (env > config.yaml > defaults)
# ==============================================================================

# --- Core Security & Behavior ---
SECRET_KEY = config.get("SECRET_KEY")
DEBUG = config.get("DEBUG", cast=bool)
ALLOWED_HOSTS = config.get("ALLOWED_HOSTS", cast=list)
CORS_ALLOWED_ORIGINS = config.get("CORS_ALLOWED_ORIGINS", cast=list)

# --- Infrastructure ---
DATABASES = {"default": dj_database_url.parse(config.get("DATABASE.URL"))}
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config.get("REDIS.URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": config.get("REDIS.MAX_CONNECTIONS", cast=int)
            },
        },
        "KEY_PREFIX": "coursereview",
    }
}

# --- Session Management ---
SESSION_COOKIE_AGE = config.get("SESSION.COOKIE_AGE", cast=int)
SESSION_SAVE_EVERY_REQUEST = config.get("SESSION.SAVE_EVERY_REQUEST", cast=bool)
SESSION_COOKIE_SECURE = not DEBUG

# --- Application-Specific Settings ---
AUTH = config.get("AUTH")
TURNSTILE_SECRET_KEY = config.get("TURNSTILE_SECRET_KEY")
AUTO_IMPORT_CRAWLED_DATA = config.get("AUTO_IMPORT_CRAWLED_DATA", cast=bool)

QUEST = config.get("QUEST")


# ==============================================================================
#  DJANGO FRAMEWORK SETTINGS
# ==============================================================================
# These settings define the application's structure and are not meant to be
# configured.

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    # django admin requires django.contrib.staticfiles to be in INSTALLED_APPS
    "django.contrib.staticfiles",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.humanize",
    "debug_toolbar",
    "rest_framework",
    "corsheaders",
    "apps.spider",
    "apps.web",
    "apps.auth",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

ROOT_URLCONF = "website.urls"
WSGI_APPLICATION = "website.wsgi.application"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

STATIC_URL = "/dummy/"  # Required by Django staticfiles but not used in this setup
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False
