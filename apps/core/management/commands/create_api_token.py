"""
Issue the DRF token the MCP server authenticates with.

    python manage.py create_api_token --username mcp-bot --create-user
    python manage.py create_api_token --username admin --rotate

The admin's "Connect an AI agent" page does the same from the browser; both go
through `apps.core.tokens.issue_token`.
"""

from django.core.management.base import BaseCommand, CommandError
from rest_framework.authtoken.models import Token

from apps.core.tokens import TokenIssueError, issue_token


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
        username = options["username"]
        had_token = Token.objects.filter(user__username=username).exists()

        try:
            issued = issue_token(username, create_user=options["create_user"], rotate=options["rotate"])
        except TokenIssueError as exc:
            raise CommandError(str(exc)) from exc

        if issued.user_created:
            self.stdout.write(self.style.SUCCESS(f"Created user '{username}' (staff, token-only access)."))
        if issued.rotated:
            self.stdout.write(self.style.WARNING("Previous token revoked."))

        key = issued.token.key
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Token for '{username}': {key}"))
        self.stdout.write("")
        self.stdout.write("Add it to your .env file:")
        self.stdout.write(f"  MBU_API_TOKEN={key}")
        self.stdout.write("")
        self.stdout.write("Use it in requests as:")
        self.stdout.write(f"  Authorization: Token {key}")

        if had_token and not options["rotate"]:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("This is the existing token. Use --rotate to replace it."))
