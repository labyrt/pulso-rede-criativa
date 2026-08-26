import os

from django.http import HttpResponse
from django.utils.cache import patch_vary_headers


class SecurityHeadersMiddleware:
    """Strict browser policy plus a deployment-controlled maintenance gate."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        maintenance_enabled = os.getenv("PULSO_MAINTENANCE_MODE", "0").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if maintenance_enabled and request.path != "/health/":
            response = HttpResponse(
                "PULSO está em manutenção por alguns minutos. Tente novamente em instantes.",
                status=503,
                content_type="text/plain; charset=utf-8",
            )
            response["Retry-After"] = "120"
            response["Cache-Control"] = "no-store"
            response["X-Robots-Tag"] = "noindex"
            return self._secure(response)

        response = self.get_response(request)
        if request.path.startswith("/api/"):
            self._protect_private_api_response(response)
        return self._secure(response)

    @staticmethod
    def _protect_private_api_response(response):
        # Authenticated API payloads can contain profile, social and payment metadata.
        # Never let browsers or intermediary caches persist them across sessions.
        response["Cache-Control"] = "no-store, private"
        response["Pragma"] = "no-cache"
        patch_vary_headers(response, ("Cookie", "Authorization"))

    def _secure(self, response):
        response.setdefault(
            "Content-Security-Policy",
            "; ".join(
                [
                    "default-src 'self'",
                    "script-src 'self' https://cdn.jsdelivr.net",
                    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
                    "font-src 'self' https://fonts.gstatic.com data:",
                    "img-src 'self' data: blob: https:",
                    "media-src 'self' blob: https:",
                    "connect-src 'self' ws: wss:",
                    "frame-src https://www.youtube.com https://player.vimeo.com",
                    "object-src 'none'",
                    "base-uri 'self'",
                    (
                        "form-action 'self' "
                        "https://github.com "
                        "https://accounts.google.com "
                        "https://www.linkedin.com "
                        "https://api.instagram.com "
                        "https://www.instagram.com "
                        "https://www.facebook.com "
                        "https://ims-na1.adobelogin.com"
                    ),
                    "frame-ancestors 'none'",
                ]
            ),
        )
        response.setdefault("Permissions-Policy", "geolocation=(), payment=(), usb=(), camera=(self), microphone=(self)")
        return response
