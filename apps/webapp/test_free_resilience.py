from pathlib import Path

from django.test import SimpleTestCase


class FreeTierResilienceTests(SimpleTestCase):
    @staticmethod
    def _script():
        root = Path(__file__).resolve().parents[2]
        return (root / "static" / "webapp" / "resilience.js").read_text(encoding="utf-8")

    def test_only_safe_read_requests_are_automatically_retried(self):
        script = self._script()
        self.assertIn('const retryable = method === "GET" || method === "HEAD";', script)
        self.assertIn('if (!retryable) return nativeFetch(input, init);', script)

    def test_transient_gateway_failures_can_recover(self):
        script = self._script()
        self.assertIn('new Set([502, 503, 504])', script)
        self.assertIn('transientStatuses.has(response.status)', script)

    def test_read_timeout_allows_a_free_instance_time_to_wake(self):
        script = self._script()
        self.assertIn('controller.abort(), 32000', script)
