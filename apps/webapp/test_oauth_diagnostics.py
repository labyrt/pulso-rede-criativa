from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from apps.accounts.adapters import classify_oauth_error
from apps.webapp.management.commands.check_integrations import github_oauth_probe


class OAuthDiagnosticTests(SimpleTestCase):
    def test_classifier_detects_missing_server_side_state_without_logging_values(self):
        request = SimpleNamespace(
            GET={"state": "sensitive-state", "code": "sensitive-code"},
        )

        self.assertEqual(classify_oauth_error(request), "state_not_found")

    def test_classifier_detects_known_provider_error(self):
        request = SimpleNamespace(GET={"error": "redirect_uri_mismatch"})

        self.assertEqual(classify_oauth_error(request), "redirect_uri_mismatch")

    @patch("apps.webapp.management.commands.check_integrations.requests.post")
    def test_github_probe_treats_bad_verification_code_as_valid_credentials(self, post):
        response = Mock()
        response.content = b'{"error":"bad_verification_code"}'
        response.status_code = 200
        response.json.return_value = {"error": "bad_verification_code"}
        post.return_value = response
        providers = {
            "github": {
                "APPS": [
                    {"client_id": "client-id", "secret": "client-secret"},
                ]
            }
        }

        self.assertEqual(github_oauth_probe(providers), "bad_verification_code")
        sent = post.call_args.kwargs["data"]
        self.assertEqual(sent["code"], "pulso-preflight-invalid-code")
        self.assertNotEqual(sent["client_secret"], "")

    @patch("apps.webapp.management.commands.check_integrations.requests.post")
    def test_github_probe_surfaces_incorrect_credentials_category(self, post):
        response = Mock()
        response.content = b'{"error":"incorrect_client_credentials"}'
        response.status_code = 200
        response.json.return_value = {"error": "incorrect_client_credentials"}
        post.return_value = response
        providers = {
            "github": {
                "APPS": [
                    {"client_id": "client-id", "secret": "client-secret"},
                ]
            }
        }

        self.assertEqual(github_oauth_probe(providers), "incorrect_client_credentials")
