# Imported on every Django process start: makes the configured Celery app the
# current app so @shared_task resolution in web views gets the redis broker
# instead of Celery's default no-op amqp app.
from .celery import app as celery_app

__all__ = ("celery_app",)
