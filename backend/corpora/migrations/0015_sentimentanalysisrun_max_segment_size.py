from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("corpora", "0014_sentimentanalysisrun_window_step"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sentimentanalysisrun",
            name="segment_size",
            field=models.IntegerField(default=60),
        ),
        migrations.AlterField(
            model_name="sentimentanalysisrun",
            name="window_step",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="sentimentanalysisrun",
            name="max_segment_size",
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
