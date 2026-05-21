from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("corpora", "0017_work_recipient_analysis_snapshot_recipient"),
    ]

    operations = [
        migrations.DeleteModel(
            name="Token",
        ),
    ]
