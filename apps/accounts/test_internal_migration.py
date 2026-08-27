from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class InternalProfileMigrationTests(SimpleTestCase):
    def test_migration_hides_named_admin_and_privileged_accounts(self):
        migration = Path(
            settings.BASE_DIR,
            "apps",
            "accounts",
            "migrations",
            "0004_hide_internal_profiles.py",
        ).read_text(encoding="utf-8")
        self.assertIn('username__iexact="labyrt_admin"', migration)
        self.assertIn("is_staff=True", migration)
        self.assertIn("is_superuser=True", migration)
        self.assertIn("update(is_hidden=True)", migration)
