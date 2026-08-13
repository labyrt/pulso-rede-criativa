from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def landing(request):
    if request.user.is_authenticated:
        return redirect("app")
    return render(request, "webapp/landing.html")


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
    return render(request, "webapp/auth.html", {"mode": mode, "social_providers": providers})


@login_required
@ensure_csrf_cookie
def app_shell(request, section="feed", username=""):
    return render(
        request,
        "webapp/app.html",
        {"section": section, "profile_username": username},
    )


def security_page(request):
    return render(request, "webapp/security.html")
