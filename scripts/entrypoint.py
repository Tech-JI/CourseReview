#!/usr/bin/env python

import shutil
import subprocess
import sys


def main() -> None:
    # If a command is provided (e.g. via compose `command:`), run it and exit.
    # This enables: `command: ["python", "django_manage.py", "migrate"]`
    if len(sys.argv) > 1:
        subprocess.run(sys.argv[1:], check=True)
        return

    if shutil.which("gunicorn"):
        subprocess.run(
            ["gunicorn", "website.wsgi:application", "--bind", "0.0.0.0:8000"],
            check=True,
        )
    else:
        print("gunicorn not found.")


if __name__ == "__main__":
    main()
