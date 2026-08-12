from django.contrib.auth.decorators import login_required
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
    return render(request, "webapp/auth.html", {"mode": mode})


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
