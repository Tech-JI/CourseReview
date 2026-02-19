#!/usr/bin/env python
import os

import django
from django.apps import apps

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website.settings")
django.setup()

User = apps.get_model("auth", "User")

username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "admin123")

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f"Superuser {username} created successfully!")
else:
    print(f"Superuser {username} already exists!")
