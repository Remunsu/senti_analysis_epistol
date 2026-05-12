from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("corpora", "0008_work_year"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="work",
            name="year",
        ),
    ]
