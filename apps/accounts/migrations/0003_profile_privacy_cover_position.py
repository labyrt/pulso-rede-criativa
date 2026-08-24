from django.db import migrations, models
import django.core.validators


def hide_internal_admin_profile(apps, schema_editor):
    Profile = apps.get_model("accounts", "Profile")
    Profile.objects.filter(user__username="labyrt-adm").update(is_hidden=True)


def unhide_internal_admin_profile(apps, schema_editor):
    Profile = apps.get_model("accounts", "Profile")
    Profile.objects.filter(user__username="labyrt-adm").update(is_hidden=False)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_profile_social_links"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="cover_position_y",
            field=models.PositiveSmallIntegerField(
                default=50,
                help_text="Posição vertical da capa, de 0 (topo) a 100 (base).",
                validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)],
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="is_hidden",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Perfis ocultos não aparecem em descoberta, conexões, posts ou URLs públicas.",
            ),
        ),
        migrations.RunPython(hide_internal_admin_profile, unhide_internal_admin_profile),
    ]
