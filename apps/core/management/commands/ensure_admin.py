"""
Create the admin login (and its API token) from environment variables.

Runs during the Vercel build, which can reach the production database even
though its credentials are marked Sensitive and cannot be pulled locally.

    DJANGO_SUPERUSER_USERNAME=...  DJANGO_SUPERUSER_PASSWORD=...  [DJANGO_SUPERUSER_EMAIL=...]
    python manage.py ensure_admin

Does nothing when the variables are unset. If the user already exists it is
left untouched (its password is never reset), so it is safe on every deploy.
The token is visible afterwards under Admin -> API tokens.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from rest_framework.authtoken.models import Token


class Command(BaseCommand):
    help = "Create a superuser and API token from DJANGO_SUPERUSER_* environment variables if missing."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
        if not username or not password:
            self.stdout.write("ensure_admin: DJANGO_SUPERUSER_USERNAME/PASSWORD not set, skipping.")
            return

        User = get_user_model()
        user = User.objects.filter(username=username).first()
        if user is None:
            user = User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"ensure_admin: created superuser '{username}'."))
        else:
            self.stdout.write(f"ensure_admin: user '{username}' already exists, left unchanged.")

        _, created = Token.objects.get_or_create(user=user)
        # Never print the key: build logs are visible to everyone on the team.
        self.stdout.write(f"ensure_admin: API token {'created' if created else 'already present'} "
                          f"(see Admin -> API tokens).")
