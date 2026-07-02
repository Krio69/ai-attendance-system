import os
import sys
from pathlib import Path

# Ensure /var/task/web is on Python path in Vercel
CURRENT_DIR = Path(__file__).resolve().parent          # .../web/attendance_project
WEB_DIR = CURRENT_DIR.parent                           # .../web
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "attendance_project.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()