from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("corpora", "0012_volume_facsimile_file"),
    ]

    operations = [
        migrations.CreateModel(
            name="SentimentAnnotationSkip",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "work",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sentiment_annotation_skip",
                        to="corpora.work",
                    ),
                ),
            ],
            options={
                "ordering": ["work"],
            },
        ),
    ]
