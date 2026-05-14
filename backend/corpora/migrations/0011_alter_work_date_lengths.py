from lxml import etree
from django.db import migrations, models


NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def first_attr(node, xpath):
    result = node.xpath(xpath, namespaces=NS)

    if not result:
        return ""

    return str(result[0]).strip()


def restore_dates_from_raw_xml(apps, schema_editor):
    Work = apps.get_model("corpora", "Work")

    for work in Work.objects.only("id", "raw_xml", "date_from", "date_to").iterator(chunk_size=1000):
        if not work.raw_xml:
            continue

        try:
            tei_node = etree.fromstring(work.raw_xml.encode("utf-8"))
        except etree.XMLSyntaxError:
            continue

        date_from = first_attr(tei_node, ".//tei:origin/tei:origDate/@from")
        date_to = first_attr(tei_node, ".//tei:origin/tei:origDate/@to")
        date_when = first_attr(tei_node, ".//tei:origin/tei:origDate/@when")

        if not date_from:
            date_from = date_when or date_to

        if not date_to:
            date_to = date_when or date_from

        if not date_from and not date_to:
            continue

        next_date_from = date_from[:100]
        next_date_to = date_to[:100]

        if work.date_from == next_date_from and work.date_to == next_date_to:
            continue

        work.date_from = next_date_from
        work.date_to = next_date_to
        work.save(update_fields=["date_from", "date_to"])


class Migration(migrations.Migration):

    dependencies = [
        ("corpora", "0010_work_dates_number_pages"),
    ]

    operations = [
        migrations.AlterField(
            model_name="work",
            name="date_from",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name="work",
            name="date_to",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.RunPython(restore_dates_from_raw_xml, migrations.RunPython.noop),
    ]
