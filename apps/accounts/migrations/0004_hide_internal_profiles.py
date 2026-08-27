from django.db import migrations
from django.db.models import Q


def hide_internal_profiles(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Profile = apps.get_model("accounts", "Profile")
    internal_ids = User.objects.filter(
        Q(username__iexact="labyrt_admin") | Q(is_staff=True) | Q(is_superuser=True)
    ).values_list("id", flat=True)
    Profile.objects.filter(user_id__in=internal_ids).update(is_hidden=True)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_profile_privacy_cover_position"),
    ]

    operations = [
        migrations.RunPython(hide_internal_profiles, migrations.RunPython.noop),
    ]
