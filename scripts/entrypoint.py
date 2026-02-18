import os
import shutil
import subprocess
import sys

import django
from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website.settings")
django.setup()
User = apps.get_model("auth", "User")

print("🔧 Running migrations...")
subprocess.run(["python3", "manage.py", "migrate"], check=True)

print("👤 Creating admin user...")
subprocess.run(["python3", "create_admin.py"], check=True)

print("🛠 Setting admin permissions...")
try:
    u = User.objects.latest("id")
    if u:
        u.is_active = True
        u.is_staff = True
        u.is_superuser = True
        u.save()
        print(f"✅ User {u.username} has been made a superuser.")
except ObjectDoesNotExist:
    print("⚠️ No user found to make admin.")


print("✅ Deployment complete!")

if shutil.which("gunicorn"):
    print("[ENTRYPOINT] Starting Gunicorn...")
    subprocess.run(
        ["gunicorn", "website.wsgi:application", "--bind", "0.0.0.0:8000"], check=True
    )
else:
    print("[ENTRYPOINT] Gunicorn not found, starting Django runserver...")
    subprocess.run(["python3", "manage.py", "runserver", "0.0.0.0:8000"], check=True)
