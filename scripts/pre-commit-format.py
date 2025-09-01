#!/usr/bin/env python3

import subprocess
import sys


def main():
    """Pre-commit formatting script"""
    print("Running formatter...")

    try:
        # Run make format and capture exit code
        result = subprocess.run(["make", "format"], check=True)

        # Format succeeded, stage the changes
        subprocess.run(["git", "add", "--update"], check=True)
        print("formatted.")
        return 0

    except subprocess.CalledProcessError:
        # Format failed, stop the commit
        print("ERROR: Formatting failed! Commit aborted.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
