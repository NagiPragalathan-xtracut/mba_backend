#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # `DJANGO_ENV` selects the settings module (development | production).
    # An explicit DJANGO_SETTINGS_MODULE always wins.
    environment = os.environ.get("DJANGO_ENV", "development")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"mbu_backend.settings.{environment}")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
