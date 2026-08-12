from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.AddField(model_name="profile", name="behance_url", field=models.URLField(blank=True, max_length=300)),
        migrations.AddField(model_name="profile", name="github_url", field=models.URLField(blank=True, max_length=300)),
        migrations.AddField(model_name="profile", name="instagram_url", field=models.URLField(blank=True, max_length=300)),
        migrations.AddField(model_name="profile", name="linkedin_url", field=models.URLField(blank=True, max_length=300)),
        migrations.AlterField(
            model_name="profile",
            name="specialty",
            field=models.CharField(
                choices=[
                    ("photography", "Fotografia"),
                    ("nail-art", "Nail art"),
                    ("hair", "Cabelo"),
                    ("painting", "Pintura"),
                    ("digital-art", "Arte digital"),
                    ("fashion", "Moda"),
                    ("music", "Música"),
                    ("design", "Design"),
                    ("tattoo", "Tatuagem"),
                    ("crafts", "Artesanato"),
                    ("development", "Desenvolvimento"),
                    ("other", "Outra expressão"),
                ],
                default="other",
                max_length=32,
            ),
        ),
    ]
