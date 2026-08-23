from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.core.cache import cache
from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def healthcheck(_request):
    status = {"status": "ok", "service": "pulso", "database": "ok"}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({"status": "degraded", "service": "pulso", "database": "unavailable"}, status=503)

    if settings.REDIS_URL:
        try:
            # A read-only cache lookup verifies TCP/TLS/auth without mutating data.
            cache.get("pulso:healthcheck")
        except Exception:
            return JsonResponse(
                {"status": "degraded", "service": "pulso", "database": "ok", "redis": "unavailable"},
                status=503,
            )
        status["redis"] = "ok"
    else:
        status["redis"] = "disabled"
    return JsonResponse(status)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("health/", healthcheck, name="healthcheck"),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-docs"),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/social/", include("apps.social.urls")),
    path("api/v1/chat/", include("apps.chat.urls")),
    path("api/v1/support/", include("apps.payments.urls")),
    path("api/v1/ai/", include("apps.assistant.urls")),
    path("", include("apps.webapp.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
