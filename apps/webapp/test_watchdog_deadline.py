from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class FeedWatchdogDeadlineTests(SimpleTestCase):
    def test_dom_mutations_do_not_reset_absolute_recovery_deadline(self):
        script = Path(settings.BASE_DIR, "static", "webapp", "lifecycle-recovery.js").read_text(encoding="utf-8")

        self.assertIn("recoveryTimer !== null && !replace", script)
        self.assertIn('diagnostic("recovery_deadline"', script)
        self.assertIn("DOM mutations must never postpone", script)
        self.assertNotIn("if (recovering || document.hidden || !loader())", script)
        self.assertIn("scheduleRecovery();", script)

    def test_recovery_path_remains_read_only(self):
        script = Path(settings.BASE_DIR, "static", "webapp", "lifecycle-recovery.js").read_text(encoding="utf-8")

        self.assertIn('method: "GET"', script)
        self.assertNotIn('method: "POST"', script)
        self.assertNotIn('method: "PATCH"', script)
        self.assertNotIn('method: "DELETE"', script)
