import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0001_initial"),
        ("social", "0002_post_support_and_development"),
    ]

    operations = [
        migrations.AddField(
            model_name="supportintent",
            name="post",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="support_intents",
                to="social.post",
            ),
        )
    ]
