from django.conf import settings
from django.core.management.base import BaseCommand


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
            "cloudinary": bool(__import__("os").getenv("CLOUDINARY_URL", "").strip()),
            "field_encryption": bool(settings.FIELD_ENCRYPTION_KEY),
            "gemini": bool(settings.GEMINI_API_KEY),
            "turn": bool(settings.WEBRTC_TURN_URL),
        }
        summary = " ".join(f"{key}={int(value)}" for key, value in checks.items())
        self.stdout.write(f"PULSO_INTEGRATION_STATUS {summary}")
