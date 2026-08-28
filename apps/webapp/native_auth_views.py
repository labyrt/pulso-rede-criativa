import base64
import hashlib
import hmac
import re
import secrets
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST


User = get_user_model()
CHALLENGE_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
CODE_RE = re.compile(r"^[A-Za-z0-9_-]{32,128}$")
VERIFIER_RE = re.compile(r"^[A-Za-z0-9_-]{43,128}$")
PENDING_TTL = 10 * 60
CODE_TTL = 90

PROVIDERS = {
    "google": ("google", "Google", "google_login", None),
    "github": ("github", "GitHub", "github_login", None),
    "linkedin": ("linkedin_oauth2", "LinkedIn", "linkedin_oauth2_login", None),
    "instagram": ("instagram", "Instagram", "instagram_login", None),
    "adobe": ("openid_connect", "Adobe / Behance", "openid_connect_login", {"provider_id": "adobe"}),
}


class PulsoNativeRedirect(HttpResponseRedirect):
    allowed_schemes = ["pulso"]


def _no_store(response):
    response["Cache-Control"] = "no-store, private"
    response["Pragma"] = "no-cache"
    return response


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _challenge_for(verifier: str) -> str:
    return _b64url(hashlib.sha256(verifier.encode("ascii")).digest())


def _provider_login_url(provider: str):
    config = PROVIDERS.get(provider)
    if not config:
        return None, None
    settings_key, label, route, kwargs = config
    if settings_key not in settings.SOCIALACCOUNT_PROVIDERS:
        return None, label
    return reverse(route, kwargs=kwargs), label


@require_GET
@never_cache
@ensure_csrf_cookie
def native_auth_start(request, provider):
    challenge = request.GET.get("challenge", "").strip()
    provider_url, provider_label = _provider_login_url(provider)
    if not provider_url or not CHALLENGE_RE.fullmatch(challenge):
        return _no_store(redirect("login-page"))

    handoff = secrets.token_urlsafe(24)
    cache.set(
        f"pulso:native-auth:pending:{handoff}",
        {"challenge": challenge, "provider": provider},
        timeout=PENDING_TTL,
    )
    next_url = f"{reverse('native-auth-complete')}?{urlencode({'handoff': handoff})}"
    response = render(
        request,
        "webapp/native_oauth_start.html",
        {
            "provider_url": provider_url,
            "provider_label": provider_label,
            "next_url": next_url,
        },
    )
    return _no_store(response)


@require_GET
@never_cache
def native_auth_complete(request):
    handoff = request.GET.get("handoff", "").strip()
    pending_key = f"pulso:native-auth:pending:{handoff}"
    pending = cache.get(pending_key) if handoff else None
    if not request.user.is_authenticated or not isinstance(pending, dict):
        return _no_store(redirect("login-page"))

    challenge = pending.get("challenge", "")
    if not CHALLENGE_RE.fullmatch(str(challenge)):
        cache.delete(pending_key)
        return _no_store(redirect("login-page"))

    code = secrets.token_urlsafe(32)
    cache.set(
        f"pulso:native-auth:code:{code}",
        {"user_id": request.user.pk, "challenge": challenge},
        timeout=CODE_TTL,
    )
    cache.delete(pending_key)
    return _no_store(PulsoNativeRedirect(f"pulso://auth/callback?{urlencode({'code': code})}"))


@csrf_exempt
@require_POST
@never_cache
def native_auth_consume(request):
    code = request.POST.get("code", "").strip()
    verifier = request.POST.get("verifier", "").strip()
    if not CODE_RE.fullmatch(code) or not VERIFIER_RE.fullmatch(verifier):
        return _no_store(redirect("login-page"))

    code_key = f"pulso:native-auth:code:{code}"
    payload = cache.get(code_key)
    if not isinstance(payload, dict):
        return _no_store(redirect("login-page"))

    expected = str(payload.get("challenge", ""))
    actual = _challenge_for(verifier)
    if not hmac.compare_digest(expected, actual):
        return _no_store(redirect("login-page"))

    user = User.objects.filter(pk=payload.get("user_id"), is_active=True).first()
    if not user:
        cache.delete(code_key)
        return _no_store(redirect("login-page"))

    cache.delete(code_key)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return _no_store(redirect("app"))
