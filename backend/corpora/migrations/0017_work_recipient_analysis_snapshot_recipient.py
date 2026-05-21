from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("corpora", "0016_sentimentanalysisresult_snapshots"),
    ]

    operations = [
        migrations.AddField(
            model_name="work",
            name="recipient",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="sentimentanalysisresult",
            name="snapshot_recipient",
            field=models.CharField(blank=True, max_length=200),
        ),
    ]
