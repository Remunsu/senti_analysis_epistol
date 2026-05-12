import re

from django.db import migrations, models


def fill_work_year(apps, schema_editor):
    Work = apps.get_model("corpora", "Work")

    for work in Work.objects.only("id", "date").iterator(chunk_size=1000):
        match = re.search(r"\d{4}", work.date or "")
        work.year = int(match.group(0)) if match else None
        work.save(update_fields=["year"])


def clear_work_year(apps, schema_editor):
    Work = apps.get_model("corpora", "Work")
    Work.objects.update(year=None)


class Migration(migrations.Migration):

    dependencies = [
        ("corpora", "0007_sentimentanalysisrun_error_message_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="work",
            name="year",
            field=models.IntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.RunPython(fill_work_year, clear_work_year),
    ]
