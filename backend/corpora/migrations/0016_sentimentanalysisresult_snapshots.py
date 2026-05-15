from django.db import migrations, models
import django.db.models.deletion


def populate_result_snapshots(apps, schema_editor):
    SentimentAnalysisResult = apps.get_model("corpora", "SentimentAnalysisResult")
    fields = [
        "original_work_id",
        "snapshot_title",
        "snapshot_author",
        "snapshot_date_from",
        "snapshot_date_to",
        "snapshot_genre",
        "snapshot_place",
    ]
    batch = []

    for result in SentimentAnalysisResult.objects.select_related("work").iterator(chunk_size=1000):
        work = result.work

        if not work:
            continue

        result.original_work_id = work.id
        result.snapshot_title = work.title
        result.snapshot_author = work.author
        result.snapshot_date_from = work.date_from
        result.snapshot_date_to = work.date_to
        result.snapshot_genre = work.genre
        result.snapshot_place = work.place
        batch.append(result)

        if len(batch) == 1000:
            SentimentAnalysisResult.objects.bulk_update(batch, fields)
            batch = []

    if batch:
        SentimentAnalysisResult.objects.bulk_update(batch, fields)


class Migration(migrations.Migration):

    dependencies = [
        ("corpora", "0015_sentimentanalysisrun_max_segment_size"),
    ]

    operations = [
        migrations.AddField(
            model_name="sentimentanalysisresult",
            name="original_work_id",
            field=models.IntegerField(db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="sentimentanalysisresult",
            name="snapshot_author",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="sentimentanalysisresult",
            name="snapshot_date_from",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="sentimentanalysisresult",
            name="snapshot_date_to",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="sentimentanalysisresult",
            name="snapshot_genre",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="sentimentanalysisresult",
            name="snapshot_place",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="sentimentanalysisresult",
            name="snapshot_title",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.RunPython(populate_result_snapshots, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="sentimentanalysisresult",
            name="original_work_id",
            field=models.IntegerField(db_index=True),
        ),
        migrations.AlterField(
            model_name="sentimentanalysisresult",
            name="work",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sentiment_results",
                to="corpora.work",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="sentimentanalysisresult",
            unique_together={("run", "original_work_id", "segment_index")},
        ),
        migrations.AlterModelOptions(
            name="sentimentanalysisresult",
            options={"ordering": ["run", "original_work_id", "segment_index"]},
        ),
    ]
