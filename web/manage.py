#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_project.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable?"
        ) from exc
        
    # --- AUTO-MIGRATE ON VERCEL ---
    # If Vercel is running the collectstatic command, trigger migrations right before it
    if 'collectstatic' in sys.argv:
        print("Vercel deployment detected: Running migrations on Neon...")
        execute_from_command_line(['manage.py', 'migrate', '--noinput'])
        
        # Automatically create a default admin login user
        print("Creating default superuser if missing...")
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            if not User.objects.filter(username='admin').exists():
                User.objects.create_superuser('admin', 'admin@example.com', 'AdminPassword123')
                print("Successfully created superuser! Username: admin | Password: AdminPassword123")
            else:
                print("Superuser 'admin' already exists.")
        except Exception as e:
            print(f"Skipping superuser creation: {e}")
    # ------------------------------

    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()