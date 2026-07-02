#!/usr/bin/env python
import os
import sys
from pathlib import Path

def main():
    base_dir = Path(__file__).resolve().parent  # .../web
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "attendance_project.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()