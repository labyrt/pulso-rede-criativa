class SecurityHeadersMiddleware:
    """Strict browser policy with an explicit allow-list for creator media."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
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
                    "form-action 'self'",
                    "frame-ancestors 'none'",
                ]
            ),
        )
        response.setdefault("Permissions-Policy", "geolocation=(), payment=(), usb=(), camera=(self), microphone=(self)")
        return response
