from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("corpora", "0006_sentimentanalysisrun_sentimentanalysisresult"),
    ]

    operations = [
        migrations.AddField(
            model_name="sentimentanalysisrun",
            name="error_message",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="sentimentanalysisrun",
            name="results_count",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="sentimentanalysisrun",
            name="status",
            field=models.CharField(
                choices=[
                    ("running", "Выполняется"),
                    ("completed", "Завершен"),
                    ("failed", "Ошибка"),
                ],
                default="completed",
                max_length=20,
            ),
        ),
    ]
