"""
WSGI config for mbu_backend project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os

from django.core.wsgi import get_wsgi_application

environment = os.environ.get("DJANGO_ENV", "development")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"mbu_backend.settings.{environment}")

application = get_wsgi_application()

# Vercel's Python runtime looks for a module-level `app`; every other host uses
# the standard `application` name above. Both point at the same WSGI callable.
app = application
