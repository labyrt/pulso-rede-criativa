from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("social", "0001_initial")]

    operations = [
        migrations.AddField(model_name="post", name="accepts_support", field=models.BooleanField(default=True)),
        migrations.AlterField(
            model_name="post",
            name="category",
            field=models.CharField(
                choices=[
                    ("photography", "Fotografia"),
                    ("beauty", "Beleza"),
                    ("art", "Arte"),
                    ("design", "Design"),
                    ("fashion", "Moda"),
                    ("music", "Música"),
                    ("process", "Processo criativo"),
                    ("opportunity", "Oportunidade"),
                    ("development", "Desenvolvimento"),
                    ("other", "Outros"),
                ],
                default="other",
                max_length=24,
            ),
        ),
    ]
