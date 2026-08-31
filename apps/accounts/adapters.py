"""Safe normalization for identities created by trusted OAuth providers."""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


User = get_user_model()
logger = logging.getLogger("pulso.oauth")
TRUSTED_VERIFIED_EMAIL_LINK_PROVIDERS = {"github", "google"}
KNOWN_PROVIDER_ERRORS = {
    "access_denied",
    "application_suspended",
    "bad_verification_code",
    "incorrect_client_credentials",
    "redirect_uri_mismatch",
    "unverified_user_email",
}


def classify_oauth_error(request, exception=None):
    """Return a non-secret failure category suitable for production logs."""
    provider_error = str(request.GET.get("error") or "").strip().lower()
    if provider_error in KNOWN_PROVIDER_ERRORS:
        return provider_error

    text = str(exception or "").lower()
    for reason in KNOWN_PROVIDER_ERRORS:
        if reason in text:
            return reason

    if exception is not None:
        if "error retrieving access token" in text:
            return "token_exchange_failed"
        if "401" in text or "unauthorized" in text:
            return "provider_unauthorized"
        return exception.__class__.__name__.lower()

    has_state = bool(request.GET.get("state"))
    has_code = bool(request.GET.get("code"))
    if has_state and has_code:
        return "state_not_found"
    if has_code and not has_state:
        return "missing_state_parameter"
    if has_state and not has_code:
        return "missing_code_parameter"
    return "unknown"


class PulsoSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Keep social login branded and safely reuse an existing local account."""

    def on_authentication_error(
        self,
        request,
        provider,
        error=None,
        exception=None,
        extra_context=None,
    ):
        provider_id = getattr(provider, "id", "unknown")
        session_cookie_present = bool(request.COOKIES.get(settings.SESSION_COOKIE_NAME))
        logger.warning(
            "PULSO_OAUTH_ERROR provider=%s reason=%s auth_error=%s has_state=%d has_code=%d session_cookie=%d exception=%s",
            provider_id,
            classify_oauth_error(request, exception),
            str(error or "unknown"),
            int(bool(request.GET.get("state"))),
            int(bool(request.GET.get("code"))),
            int(session_cookie_present),
            exception.__class__.__name__ if exception is not None else "none",
        )
        return super().on_authentication_error(
            request,
            provider,
            error=error,
            exception=exception,
            extra_context=extra_context,
        )

    def pre_social_login(self, request, sociallogin):
        """Connect trusted providers only when they prove a verified e-mail.

        PULSO accounts can be created by the local API, so they do not always
        have an allauth ``EmailAddress`` row. Without this bridge, a person who
        later signs in with the same verified Google or GitHub e-mail could be
        sent to a duplicate signup flow instead of their existing PULSO account.
        """

        if sociallogin.is_existing:
            return
        if sociallogin.account.provider not in TRUSTED_VERIFIED_EMAIL_LINK_PROVIDERS:
            return

        verified_emails = {
            address.email.strip().casefold()
            for address in sociallogin.email_addresses
            if getattr(address, "verified", False) and getattr(address, "email", "")
        }
        for email in verified_emails:
            matches = list(User.objects.filter(email__iexact=email, is_active=True)[:2])
            if len(matches) == 1:
                sociallogin.connect(request, matches[0])
                return

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        profile = user.profile
        data = sociallogin.account.extra_data or {}
        display_name = (
            data.get("name")
            or " ".join(filter(None, (data.get("given_name"), data.get("family_name"))))
            or user.get_full_name()
            or user.username
        )
        profile.display_name = str(display_name)[:80]

        provider = sociallogin.account.provider
        username = data.get("login") or data.get("username")
        if provider == "github" and username:
            profile.github_url = f"https://github.com/{username}"
        elif provider == "instagram" and username:
            profile.instagram_url = f"https://instagram.com/{username}"

        picture = str(data.get("picture") or "").strip()
        if provider == "google" and picture.startswith("https://") and not profile.avatar_url:
            profile.avatar_url = picture[:500]

        profile.save()
        return user
