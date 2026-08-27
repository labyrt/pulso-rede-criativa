import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.core.cache import cache
from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.webapp.database_guard import validate_database_target


def _database_unavailable_response():
    response = JsonResponse(
        {"status": "degraded", "service": "pulso", "database": "unavailable"},
        status=503,
    )
    response["Retry-After"] = "3"
    response["Cache-Control"] = "no-store"
    return response


def healthcheck(_request):
    status = {"status": "ok", "service": "pulso", "database": "ok"}

    require_neon = os.getenv("PULSO_REQUIRE_NEON_DATABASE", "0").strip() == "1"
    expected_database = os.getenv("PULSO_EXPECTED_DATABASE_NAME", "").strip()
    if require_neon or expected_database:
        try:
            validate_database_target(
                os.getenv("DATABASE_URL", ""),
                require_neon=require_neon,
                expected_database=expected_database,
            )
        except ValueError:
            return JsonResponse(
                {"status": "degraded", "service": "pulso", "database": "unexpected_target"},
                status=503,
            )

    try:
        # Scale-to-zero can invalidate an existing TCP session while Django is
        # still alive. Discard it before probing and close it immediately on a
        # failed reconnect so the next request starts from a clean state.
        connection.close_if_unusable_or_obsolete()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        connection.close()
        return _database_unavailable_response()

    if settings.REDIS_URL:
        try:
            # A read-only cache lookup verifies TCP/TLS/auth without mutating data.
            cache.get("pulso:healthcheck")
        except Exception:
            response = JsonResponse(
                {"status": "degraded", "service": "pulso", "database": "ok", "redis": "unavailable"},
                status=503,
            )
            response["Retry-After"] = "3"
            response["Cache-Control"] = "no-store"
            return response
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
