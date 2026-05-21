from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("corpora", "0018_delete_token"),
    ]

    operations = [
        migrations.AddField(
            model_name="sentimentanalysisrun",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="sentiment_analysis_runs",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
