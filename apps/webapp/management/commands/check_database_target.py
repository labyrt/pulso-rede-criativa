import os

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.webapp.database_guard import validate_database_target


class Command(BaseCommand):
    help = "Verify that production is connected to the expected database before migrations run."

    def handle(self, *args, **options):
        require_neon = os.getenv("PULSO_REQUIRE_NEON_DATABASE", "0").strip() == "1"
        expected_database = os.getenv("PULSO_EXPECTED_DATABASE_NAME", "").strip()

        if not require_neon and not expected_database:
            self.stdout.write("PULSO_DATABASE_TARGET guard=disabled")
            return

        try:
            target = validate_database_target(
                os.getenv("DATABASE_URL", ""),
                require_neon=require_neon,
                expected_database=expected_database,
            )
        except ValueError as exc:
            raise CommandError(f"Production database guard failed: {exc}.") from exc

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

        self.stdout.write(
            self.style.SUCCESS(
                "PULSO_DATABASE_TARGET "
                f"provider={target['provider']} database={actual_database} verified=1"
            )
        )
