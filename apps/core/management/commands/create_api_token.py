"""
Issue the DRF token the MCP server authenticates with.

    python manage.py create_api_token --username mcp-bot --create-user
    python manage.py create_api_token --username admin --rotate
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from rest_framework.authtoken.models import Token


class Command(BaseCommand):
    help = "Create (or show) the API token used by the MCP server and other API clients."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="User the token belongs to.")
        parser.add_argument(
            "--create-user",
            action="store_true",
            help="Create the user if it does not exist. Created users are staff with an unusable password.",
        )
        parser.add_argument(
            "--rotate",
            action="store_true",
            help="Delete the existing token and issue a fresh one. Invalidates the old key immediately.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            if not options["create_user"]:
                raise CommandError(
                    f"No user named '{username}'. Re-run with --create-user to create one, "
                    f"or use an existing username."
                )
            # An unusable password means this account can only ever act through
            # its API token - it cannot be used to log into the admin.
            user = User.objects.create_user(username=username, is_staff=True)
            user.set_unusable_password()
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created user '{username}' (staff, token-only access)."))

        if options["rotate"]:
            deleted, _ = Token.objects.filter(user=user).delete()
            if deleted:
                self.stdout.write(self.style.WARNING("Previous token revoked."))

        token, created = Token.objects.get_or_create(user=user)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Token for '{username}': {token.key}"))
        self.stdout.write("")
        self.stdout.write("Add it to your .env file:")
        self.stdout.write(f"  MBU_API_TOKEN={token.key}")
        self.stdout.write("")
        self.stdout.write("Use it in requests as:")
        self.stdout.write(f"  Authorization: Token {token.key}")

        if not created and not options["rotate"]:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("This is the existing token. Use --rotate to replace it."))
