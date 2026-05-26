from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("corpora", "0020_volume_pdf_page_corrections"),
    ]

    operations = [
        migrations.DeleteModel(
            name="SentimentAnnotationSkip",
        ),
        migrations.DeleteModel(
            name="SentimentFragmentLabel",
        ),
    ]
