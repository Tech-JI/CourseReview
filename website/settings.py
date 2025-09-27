import os
from dotenv import load_dotenv

load_dotenv()

TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY")
SIGNUP_QUEST_API_KEY = os.getenv("SIGNUP_QUEST_API_KEY")
SIGNUP_QUEST_URL = os.getenv("SIGNUP_QUEST_URL")
SIGNUP_QUEST_QUESTIONID = os.getenv("SIGNUP_QUEST_QUESTIONID")
LOGIN_QUEST_API_KEY = os.getenv("LOGIN_QUEST_API_KEY")
LOGIN_QUEST_URL = os.getenv("LOGIN_QUEST_URL")
LOGIN_QUEST_QUESTIONID = os.getenv("LOGIN_QUEST_QUESTIONID")
RESET_QUEST_API_KEY = os.getenv("RESET_QUEST_API_KEY")
RESET_QUEST_URL = os.getenv("RESET_QUEST_URL")
RESET_QUEST_QUESTIONID = os.getenv("RESET_QUEST_QUESTIONID")

FRONTEND_URL = os.getenv("FRONTEND_URL")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# INSTALLED_APPS
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "debug_toolbar",
    "pipeline",
    "crispy_forms",
    "crispy_bootstrap4",
    "django_celery_beat",
    "django_celery_results",
    "rest_framework",
    "corsheaders",
    "apps.analytics",
    "apps.recommendations",
    "apps.spider",
    "apps.web",
    "apps.auth",
]

# MIDDLEWARE
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

# TEMPLATES
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
            ],
        },
    }
]

CRISPY_TEMPLATE_PACK = "bootstrap4"

WSGI_APPLICATION = "website.wsgi.application"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

CELERY_RESULT_BACKEND = "django-db"
CELERY_TIMEZONE = "Asia/Shanghai"

AUTO_IMPORT_CRAWLED_DATA = os.getenv("AUTO_IMPORT_CRAWLED_DATA", "True") == "True"

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_ROOT = "staticfiles"
STATIC_URL = "/static/"
STATICFILES_STORAGE = "pipeline.storage.ManifestStaticFilesStorage"
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "pipeline.finders.PipelineFinder",
]

# Pipeline configuration
PIPELINE = {
    "JAVASCRIPT": {
        "app": {
            "source_filenames": [
                "js/plugins.js",
                "js/vendor/jquery.highlight-5.js",
                "js/web/base.jsx",
                "js/web/common.jsx",
                "js/web/landing.jsx",
                "js/web/current_term.jsx",
                "js/web/course_detail.jsx",
                "js/web/course_review_search.jsx",
            ],
            "output_filename": "js/app.js",
        }
    },
    "STYLESHEETS": {
        "app": {
            "source_filenames": [
                "css/web/base.css",
                "css/web/current_term.css",
                "css/web/course_detail.css",
                "css/web/course_review_search.css",
                "css/web/landing.css",
                "css/web/auth.css",
            ],
            "output_filename": "css/app.css",
            "extra_context": {
                "media": "screen,projection",
            },
        }
    },
}

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Session settings
SESSION_COOKIE_AGE = int(os.getenv("SESSION_COOKIE_AGE", "2592000"))
SESSION_SAVE_EVERY_REQUEST = os.getenv("SESSION_SAVE_EVERY_REQUEST", "True") == "True"
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS").split(",")

# OAuth settings
AUTH = {
    "OTP_TIMEOUT": int(os.getenv("OTP_TIMEOUT", "120")),
    "TEMP_TOKEN_TIMEOUT": int(os.getenv("TEMP_TOKEN_TIMEOUT", "600")),
    "TOKEN_RATE_LIMIT": int(os.getenv("TOKEN_RATE_LIMIT", "5")),
    "TOKEN_RATE_LIMIT_TIME": int(os.getenv("TOKEN_RATE_LIMIT_TIME", "600")),
    "PASSWORD_LENGTH_MIN": int(os.getenv("PASSWORD_LENGTH_MIN", "10")),
    "PASSWORD_LENGTH_MAX": int(os.getenv("PASSWORD_LENGTH_MAX", "32")),
    "QUEST_BASE_URL": os.getenv(
        "QUEST_BASE_URL", "https://wj.sjtu.edu.cn/api/v1/public/export"
    ),
    "EMAIL_DOMAIN_NAME": os.getenv("EMAIL_DOMAIN_NAME", "sjtu.edu.cn"),
}

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
    CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    CORS_ALLOWED_ORIGINS = [
        origin.strip() for origin in CORS_ALLOWED_ORIGINS if origin.strip()
    ]
    CORS_ALLOWED_ORIGINS.extend(
        [
            FRONTEND_URL,
        ]
    )


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


CELERY_BROKER_URL = os.getenv("REDIS_URL")


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/
STATICFILES_DIRS = (os.path.join(BASE_DIR, "static"),)

ROOT_ASSETS_DIR = os.path.join(BASE_DIR, "root_assets")

SESSION_COOKIE_SECURE = not DEBUG

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 100},
        },
        "KEY_PREFIX": "coursereview",
    }
}
