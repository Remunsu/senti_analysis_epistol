from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("corpora", "0019_sentimentanalysisrun_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="volume",
            name="pdf_page_offset",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="volume",
            name="pdf_extra_pages",
            field=models.TextField(blank=True),
        ),
    ]
