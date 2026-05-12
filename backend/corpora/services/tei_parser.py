import re
from pathlib import Path
from lxml import etree
from django.db import transaction

from corpora.models import Volume, Work, Token


NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def clean_text(value: str) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def first_text(node, xpath: str) -> str:
    result = node.xpath(xpath, namespaces=NS)
    if not result:
        return ""
    if isinstance(result[0], etree._Element):
        return clean_text("".join(result[0].itertext()))
    return clean_text(str(result[0]))


def first_attr(node, xpath: str) -> str:
    result = node.xpath(xpath, namespaces=NS)
    if not result:
        return ""
    return clean_text(str(result[0]))


def to_int(value: str):
    if value in (None, ""):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_xml_file(path: str):
    text = Path(path).read_text(encoding="utf-8")
    text = re.sub(r'encoding="[^"]+"', 'encoding="UTF-8"', text, count=1)

    parser = etree.XMLParser(
        recover=True,
        huge_tree=True,
        resolve_entities=False,
        no_network=True,
    )
    return etree.fromstring(text.encode("utf-8"), parser=parser)


def extract_volume_data(root) -> dict:
    return {
        "source_id": first_text(root, "./tei:teiHeader//tei:idno")[:20],
        "number": to_int(first_attr(root, "./tei:teiHeader//tei:num/@value")),
        "author": first_text(root, "./tei:teiHeader//tei:author")[:50],
        "title_short": first_text(root, "./tei:teiHeader//tei:title[@type='short']")[:100],
        "title": first_text(root, "./tei:teiHeader//tei:title[@type='main']")[:200],
    }


def extract_plain_text(tei_node) -> str:
    text_node = tei_node.xpath("./tei:text", namespaces=NS)
    if not text_node:
        return ""

    parts = []

    for el in text_node[0].iter():
        tag = etree.QName(el).localname

        if tag == "w":
            word = "".join(el.xpath("./text()", namespaces=NS))
            word = clean_text(word)
            if word:
                parts.append(word)

        elif tag == "pc":
            pc = clean_text("".join(el.itertext()))
            if pc:
                parts.append(pc)

        elif tag in {"lb", "pb"}:
            parts.append("\n")

    text = " ".join(parts)

    text = text.replace(" ,", ",")
    text = text.replace(" .", ".")
    text = text.replace(" :", ":")
    text = text.replace(" ;", ";")
    text = text.replace(" !", "!")
    text = text.replace(" ?", "?")
    text = re.sub(r"\s+\n\s+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def extract_tokens(work: Work, tei_node):
    token_objects = []

    words = tei_node.xpath(".//tei:text//tei:w", namespaces=NS)

    for index, w in enumerate(words):
        word_text = clean_text("".join(w.xpath("./text()", namespaces=NS)))
        lemma = clean_text(w.get("lemma", ""))

        pos = first_attr(w,'./tei:fs/tei:f[@name="category"]/tei:symbol/@value')

        if not word_text or not lemma:
            continue

        token_objects.append(
            Token(
                work=work,
                text_position=index,
                text=word_text[:20],
                lemma=lemma[:20],
                pos=pos[:20],
            )
        )

    Token.objects.bulk_create(token_objects, batch_size=2000)


def extract_work_data(tei_node, volume: Volume) -> dict:
    source_id = first_text(tei_node, ".//tei:sourceDesc//tei:msIdentifier/tei:idno")
    page_number = to_int(first_attr(tei_node, ".//tei:sourceDesc//tei:head/tei:num/@value"))

    date = first_attr(tei_node, ".//tei:origin/tei:origDate/@to")
    place = first_text(tei_node, ".//tei:origin/tei:origPlace")

    author = first_text(tei_node, ".//tei:msContents/tei:msItem/tei:author")
    language = first_attr(tei_node, ".//tei:msContents/tei:msItem/tei:textLang/@otherLangs")

    title_desc = first_text(tei_node, './/tei:msContents/tei:msItem/tei:title[@type="desc"]')
    title_short = first_text(tei_node, './/tei:msContents/tei:msItem/tei:title[@type="short"]')
    title = first_text(tei_node, './/tei:msContents/tei:msItem/tei:title[@type="main"]')

    genre = first_text(tei_node, ".//tei:encodingDesc//tei:catDesc")

    raw_xml = etree.tostring(tei_node, encoding="unicode")
    plain_text = extract_plain_text(tei_node)

    return {
        "volume": volume,
        "source_id": source_id[:20],
        "note": "",
        "page_number": page_number,
        "date": date[:20],
        "place": place[:50],
        "author": (author or volume.author)[:50],
        "language": language[:20],
        "title_desc": title_desc[:200],
        "title_short": title_short[:100],
        "title": title[:200],
        "genre": genre[:20],
        "plain_text": plain_text,
        "raw_xml": raw_xml,
    }


def apply_volume_data(volume: Volume, volume_data: dict):
    for field, value in volume_data.items():
        setattr(volume, field, value)

    volume.save()


def create_work_from_tei(tei_node, volume: Volume):
    work_data = extract_work_data(tei_node, volume)
    work = Work.objects.create(**work_data)
    extract_tokens(work, tei_node)

    return work


@transaction.atomic
def parse_volume(volume: Volume):
    root = parse_xml_file(volume.xml_file.path)

    apply_volume_data(volume, extract_volume_data(root))

    volume.works.all().delete()

    tei_nodes = root.xpath("./tei:TEI", namespaces=NS)

    created_works = []

    for tei_node in tei_nodes:
        created_works.append(create_work_from_tei(tei_node, volume))

    return created_works
