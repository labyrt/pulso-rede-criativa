from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("social", "0002_post_support_and_development")]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="kind",
            field=models.CharField(
                choices=[
                    ("follow", "Novo seguidor"),
                    ("like", "Curtida"),
                    ("comment", "Comentário"),
                    ("repost", "Compartilhamento"),
                    ("post", "Nova publicação"),
                    ("message", "Mensagem"),
                    ("call", "Ligação"),
                ],
                max_length=16,
            ),
        ),
    ]
