from django.db import migrations, models


def copy_date_to_date_from(apps, schema_editor):
    Work = apps.get_model("corpora", "Work")

    for work in Work.objects.only("id", "date_to").iterator(chunk_size=1000):
        if not work.date_from:
            work.date_from = work.date_to
            work.save(update_fields=["date_from"])


def copy_date_from_to_date_to(apps, schema_editor):
    Work = apps.get_model("corpora", "Work")

    for work in Work.objects.only("id", "date_from").iterator(chunk_size=1000):
        if not work.date_to:
            work.date_to = work.date_from
            work.save(update_fields=["date_to"])


class Migration(migrations.Migration):

    dependencies = [
        ("corpora", "0009_remove_work_year"),
    ]

    operations = [
        migrations.RenameField(
            model_name="work",
            old_name="page_number",
            new_name="number",
        ),
        migrations.RenameField(
            model_name="work",
            old_name="date",
            new_name="date_to",
        ),
        migrations.AddField(
            model_name="work",
            name="date_from",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="work",
            name="pages",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.RunPython(copy_date_to_date_from, copy_date_from_to_date_to),
    ]
