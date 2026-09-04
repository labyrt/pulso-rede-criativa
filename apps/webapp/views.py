from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie

from apps.webapp.widget_views import build_widget_summary


@ensure_csrf_cookie
def landing(request):
    if request.user.is_authenticated:
        return redirect("app")
    return render(request, "webapp/landing.html")


@never_cache
@ensure_csrf_cookie
def auth_page(request, mode):
    if request.user.is_authenticated:
        return redirect("app")
    providers = [
        {
            "id": "google",
            "label": "Google",
            "mark": "G",
            "enabled": "google" in settings.SOCIALACCOUNT_PROVIDERS,
            "url": reverse("google_login"),
        },
        {
            "id": "github",
            "label": "GitHub",
            "mark": "GH",
            "enabled": "github" in settings.SOCIALACCOUNT_PROVIDERS,
            "url": reverse("github_login"),
        },
        {
            "id": "linkedin",
            "label": "LinkedIn",
            "mark": "in",
            "enabled": "linkedin_oauth2" in settings.SOCIALACCOUNT_PROVIDERS,
            "url": reverse("linkedin_oauth2_login"),
        },
        {
            "id": "instagram",
            "label": "Instagram",
            "mark": "IG",
            "enabled": "instagram" in settings.SOCIALACCOUNT_PROVIDERS,
            "url": reverse("instagram_login"),
        },
        {
            "id": "adobe",
            "label": "Adobe / Behance",
            "mark": "Be",
            "enabled": "openid_connect" in settings.SOCIALACCOUNT_PROVIDERS,
            "url": reverse("openid_connect_login", kwargs={"provider_id": "adobe"}),
        },
    ]
    enabled_providers = [provider for provider in providers if provider["enabled"]]
    is_native_android = "PULSO-Android/" in request.headers.get("User-Agent", "")
    return render(
        request,
        "webapp/auth.html",
        {
            "mode": mode,
            "social_providers": enabled_providers,
            "is_native_android": is_native_android,
        },
    )


@login_required
@ensure_csrf_cookie
def app_shell(request, section="feed", username=""):
    return render(
        request,
        "webapp/app.html",
        {
            "section": section,
            "profile_username": username,
            "widget_summary": build_widget_summary(request.user),
        },
    )


def security_page(request):
    return render(request, "webapp/security.html")


def pwa_manifest(_request):
    response = JsonResponse(
        {
            "id": "/",
            "name": "PULSO — Rede Criativa",
            "short_name": "PULSO",
            "description": "Rede para criar, conectar e movimentar a economia criativa.",
            "lang": "pt-BR",
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "orientation": "any",
            "background_color": "#f7f6f2",
            "theme_color": "#0b0b0c",
            "categories": ["social", "lifestyle"],
            "icons": [
                {
                    "src": "/static/webapp/icons/pulso-192.png",
                    "sizes": "192x192",
                    "type": "image/png",
                    "purpose": "any",
                },
                {
                    "src": "/static/webapp/icons/pulso-512.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "any",
                },
                {
                    "src": "/static/webapp/icons/pulso-maskable-512.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "maskable",
                },
            ],
            "shortcuts": [
                {"name": "Feed", "short_name": "Feed", "url": "/app/"},
                {"name": "Explorar", "short_name": "Explorar", "url": "/explorar/"},
                {"name": "Mensagens", "short_name": "Mensagens", "url": "/mensagens/"},
            ],
        },
        json_dumps_params={"ensure_ascii": False},
    )
    response["Content-Type"] = "application/manifest+json"
    response["Cache-Control"] = "public, max-age=3600"
    return response


def service_worker(_request):
    source = Path(settings.BASE_DIR, "static", "webapp", "service-worker.js").read_text(encoding="utf-8")
    response = HttpResponse(source, content_type="application/javascript; charset=utf-8")
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["Service-Worker-Allowed"] = "/"
    return response
