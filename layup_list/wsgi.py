"""
WSGI config for layup_list project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/dev/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "layup_list.settings")

from django.core.wsgi import get_wsgi_application
from whitenoise.django import DjangoWhiteNoise
from settings import ROOT_ASSETS_DIR

application = get_wsgi_application()
application = DjangoWhiteNoise(application)
application.add_files(ROOT_ASSETS_DIR)
