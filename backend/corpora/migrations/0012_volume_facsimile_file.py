from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("corpora", "0011_alter_work_date_lengths"),
    ]

    operations = [
        migrations.AddField(
            model_name="volume",
            name="facsimile_file",
            field=models.FileField(blank=True, upload_to="volume_facsimiles/"),
        ),
    ]
