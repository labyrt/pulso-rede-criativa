import os

import requests
from django.conf import settings
from django.core.management.base import BaseCommand


_GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
_KNOWN_GITHUB_ERRORS = {
    "bad_verification_code",
    "incorrect_client_credentials",
    "redirect_uri_mismatch",
    "unverified_user_email",
}


def _github_callback_url():
    origin = (
        os.getenv("PULSO_PUBLIC_ORIGIN", "").strip()
        or os.getenv("RENDER_EXTERNAL_URL", "").strip()
    )
    if not origin:
        hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()
        if hostname:
            origin = f"https://{hostname}"
    if not origin:
        origin = "https://pulso-rede-criativa.onrender.com"
    return f"{origin.rstrip('/')}/accounts/github/login/callback/"


def github_oauth_probe(providers):
    """Validate the configured GitHub OAuth app without exposing credentials."""
    github = providers.get("github") or {}
    apps = github.get("APPS") or []
    if not apps:
        return "not_configured"
    app = apps[0]
    client_id = str(app.get("client_id") or "").strip()
    secret = str(app.get("secret") or "").strip()
    if not client_id or not secret:
        return "not_configured"

    try:
        response = requests.post(
            _GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": client_id,
                "client_secret": secret,
                "code": "pulso-preflight-invalid-code",
                "redirect_uri": _github_callback_url(),
            },
            timeout=8,
        )
        payload = response.json() if response.content else {}
    except (requests.RequestException, ValueError):
        return "unavailable"

    error = str(payload.get("error") or "").strip()
    if error in _KNOWN_GITHUB_ERRORS:
        return error
    if payload.get("access_token"):
        return "unexpected_token"
    return f"unexpected_http_{response.status_code}"


def turn_ready():
    return bool(
        settings.WEBRTC_TURN_URL
        and settings.WEBRTC_TURN_USERNAME
        and settings.WEBRTC_TURN_CREDENTIAL
    )


class Command(BaseCommand):
    help = "Print a non-secret readiness summary for production integrations."

    def handle(self, *args, **options):
        providers = settings.SOCIALACCOUNT_PROVIDERS
        checks = {
            "database": bool(settings.DATABASES.get("default")),
            "redis": bool(settings.REDIS_URL),
            "google_oauth": "google" in providers,
            "github_oauth": "github" in providers,
            "linkedin_oauth": "linkedin_oauth2" in providers,
            "instagram_oauth": "instagram" in providers,
            "adobe_oauth": "openid_connect" in providers,
            "cloudinary": bool(os.getenv("CLOUDINARY_URL", "").strip()),
            "field_encryption": bool(settings.FIELD_ENCRYPTION_KEY),
            "gemini": bool(settings.GEMINI_API_KEY and settings.GEMINI_MODEL),
            "turn": turn_ready(),
        }
        summary = " ".join(f"{key}={int(value)}" for key, value in checks.items())
        self.stdout.write(f"PULSO_INTEGRATION_STATUS {summary}")
        self.stdout.write(f"PULSO_GITHUB_OAUTH_PROBE result={github_oauth_probe(providers)}")
        self.stdout.write(f"PULSO_AI_MODEL model={settings.GEMINI_MODEL}")

        if not checks["gemini"]:
            self.stderr.write(
                self.style.WARNING(
                    "PULSO_DEGRADED ai=1 reason=GEMINI_API_KEY_missing caption assistant will preserve drafts without generative rewriting"
                )
            )
        if not checks["turn"]:
            self.stderr.write(
                self.style.WARNING(
                    "PULSO_DEGRADED calls=1 reason=TURN_incomplete WebRTC may fail on restrictive NAT/mobile networks"
                )
            )
