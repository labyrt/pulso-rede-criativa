"""Safe normalization for identities created by trusted OAuth providers."""

from django.contrib.auth import get_user_model

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


User = get_user_model()
TRUSTED_VERIFIED_EMAIL_LINK_PROVIDERS = {"github", "google"}


class PulsoSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Keep social login branded and safely reuse an existing local account."""

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
