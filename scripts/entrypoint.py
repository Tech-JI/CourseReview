#!/usr/bin/env python
import os
import shutil
import subprocess
import sys

import django
from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist

# --- Django setup ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website.settings")
django.setup()

User = apps.get_model("auth", "User")

# --- Step 1: Migrations ---
print("🔧 Running migrations...")
subprocess.run(["python", "manage.py", "migrate"], check=True)

# --- Step 2: Create or fix admin user ---
print("👤 Ensuring admin user exists and has superuser permissions...")

username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "admin123")

try:
    u = User.objects.get(username=username)

    changed = False
    # Ensure correct privilege flags (do NOT change password for existing user)
    if not u.is_active:
        u.is_active = True
        changed = True
    if not u.is_staff:
        u.is_staff = True
        changed = True
    if not u.is_superuser:
        u.is_superuser = True
        changed = True

    # Optional: keep email in sync (harmless)
    if email and u.email != email:
        u.email = email
        changed = True

    if changed:
        u.save()
        print(f"✅ Admin user '{username}' updated/verified (password unchanged).")
    else:
        print(f"✅ Admin user '{username}' already correct (password unchanged).")

except ObjectDoesNotExist:
    # Only set password on first creation
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"✅ Superuser '{username}' created successfully!")

# --- Step 3: Start app server ---
print("✅ Deployment complete!")

if shutil.which("gunicorn"):
    print("[ENTRYPOINT] Starting Gunicorn...")
    subprocess.run(
        ["gunicorn", "website.wsgi:application", "--bind", "0.0.0.0:8000"],
        check=True,
    )
else:
    print("[ENTRYPOINT] Gunicorn not found, starting Django runserver...")
    subprocess.run(
        ["python", "manage.py", "runserver", "0.0.0.0:8000"],
        check=True,
    )
