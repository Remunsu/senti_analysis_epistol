from django.db import migrations, models


def preserve_existing_window_steps(apps, schema_editor):
    SentimentAnalysisRun = apps.get_model("corpora", "SentimentAnalysisRun")

    for run in SentimentAnalysisRun.objects.all().only("id", "segment_size"):
        run.window_step = run.segment_size
        run.save(update_fields=["window_step"])


class Migration(migrations.Migration):

    dependencies = [
        ("corpora", "0013_sentimentannotationskip"),
    ]

    operations = [
        migrations.AddField(
            model_name="sentimentanalysisrun",
            name="window_step",
            field=models.IntegerField(default=25),
        ),
        migrations.RunPython(preserve_existing_window_steps, migrations.RunPython.noop),
    ]
