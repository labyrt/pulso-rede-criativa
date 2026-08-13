"""Safe normalization for identities created by trusted OAuth providers."""

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class PulsoSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Complete the public profile without auto-linking existing accounts."""

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
        profile.save()
        return user
