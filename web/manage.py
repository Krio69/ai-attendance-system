#!/usr/bin/env python
import os
import sys
from pathlib import Path

def main():
    root = Path(__file__).resolve().parent
    web_dir = root / "web"

    # Make "attendance_project" importable
    sys.path.insert(0, str(web_dir))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "attendance_project.settings")

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()