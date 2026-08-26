import os
from urllib.parse import urlparse

from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = "Verify that production is connected to the expected database before migrations run."

    def handle(self, *args, **options):
        require_neon = os.getenv("PULSO_REQUIRE_NEON_DATABASE", "0").strip() == "1"
        expected_database = os.getenv("PULSO_EXPECTED_DATABASE_NAME", "").strip()

        if not require_neon and not expected_database:
            self.stdout.write("PULSO_DATABASE_TARGET guard=disabled")
            return

        database_url = os.getenv("DATABASE_URL", "").strip()
        if not database_url:
            raise CommandError("Production database guard failed: DATABASE_URL is not configured.")

        parsed = urlparse(database_url)
        host = (parsed.hostname or "").lower().rstrip(".")
        configured_database = parsed.path.lstrip("/")

        if require_neon and not host.endswith(".neon.tech"):
            raise CommandError(
                "Production database guard rejected DATABASE_URL: expected a Neon database endpoint."
            )

        if expected_database and configured_database != expected_database:
            raise CommandError(
                "Production database guard rejected DATABASE_URL: unexpected database name."
            )

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_database()")
                actual_database = cursor.fetchone()[0]
        except Exception as exc:
            raise CommandError(
                "Production database guard could not establish a database connection."
            ) from exc

        if expected_database and actual_database != expected_database:
            raise CommandError(
                "Production database guard connected to an unexpected database."
            )

        provider = "neon" if host.endswith(".neon.tech") else "other"
        self.stdout.write(
            self.style.SUCCESS(
                f"PULSO_DATABASE_TARGET provider={provider} database={actual_database} verified=1"
            )
        )
