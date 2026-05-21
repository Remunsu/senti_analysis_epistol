import re
import shutil
import subprocess
from pathlib import Path


def add_djvu_outline_to_pdf(djvu_path: Path, pdf_path: Path) -> bool:
    outline_text = read_djvu_outline(djvu_path)

    if not outline_text:
        return False

    outline = parse_djvu_outline(outline_text)

    if not outline:
        return False

    return write_pdf_outline(pdf_path, outline)


def read_djvu_outline(djvu_path: Path) -> str:
    djvused_path = shutil.which("djvused")

    if not djvused_path:
        return ""

    try:
        result = subprocess.run(
            [djvused_path, "-u", str(djvu_path), "-e", "print-outline"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ""

    return result.stdout.strip()


def parse_djvu_outline(outline_text: str):
    tokens = tokenize_outline(outline_text)

    if not tokens:
        return []

    parsed = parse_tokens(tokens)

    if not isinstance(parsed, list):
        return []

    if parsed and parsed[0] == "bookmarks":
        parsed = parsed[1:]

    return [
        item
        for item in (parse_outline_item(node) for node in parsed)
        if item
    ]


def tokenize_outline(text: str):
    tokens = []
    index = 0

    while index < len(text):
        char = text[index]

        if char.isspace():
            index += 1
            continue

        if char in "()":
            tokens.append(char)
            index += 1
            continue

        if char == '"':
            value, index = read_quoted_string(text, index + 1)
            tokens.append(value)
            continue

        start = index

        while index < len(text) and not text[index].isspace() and text[index] not in "()":
            index += 1

        tokens.append(text[start:index])

    return tokens


def read_quoted_string(text: str, index: int):
    chars = []
    escaped = False

    while index < len(text):
        char = text[index]
        index += 1

        if escaped:
            chars.append(char)
            escaped = False
            continue

        if char == "\\":
            escaped = True
            continue

        if char == '"':
            break

        chars.append(char)

    return "".join(chars), index


def parse_tokens(tokens):
    node, index = parse_node(tokens, 0)

    if index != len(tokens):
        return []

    return node


def parse_node(tokens, index):
    if index >= len(tokens):
        return [], index

    token = tokens[index]

    if token != "(":
        return token, index + 1

    index += 1
    items = []

    while index < len(tokens) and tokens[index] != ")":
        item, index = parse_node(tokens, index)
        items.append(item)

    if index < len(tokens) and tokens[index] == ")":
        index += 1

    return items, index


def parse_outline_item(node):
    if not isinstance(node, list) or len(node) < 2:
        return None

    title = str(node[0]).strip()
    destination = str(node[1]).strip()
    page_number = parse_outline_page_number(destination)

    if not title or page_number is None:
        return None

    children = [
        item
        for item in (parse_outline_item(child) for child in node[2:] if isinstance(child, list))
        if item
    ]

    return {
        "title": title,
        "page_number": page_number,
        "children": children,
    }


def parse_outline_page_number(destination: str):
    destination = str(destination or "")

    for pattern in (r"page[-_ ]?(\d+)", r"#(\d+)$", r"(\d+)$"):
        match = re.search(pattern, destination, flags=re.IGNORECASE)

        if match:
            page_number = int(match.group(1))
            return max(page_number - 1, 0)

    return None


def write_pdf_outline(pdf_path: Path, outline) -> bool:
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)

    pages_count = len(reader.pages)

    if pages_count < 1:
        return False

    added_count = add_outline_items(writer, outline, pages_count)

    if not added_count:
        return False

    temp_path = pdf_path.with_suffix(f"{pdf_path.suffix}.outline.tmp")

    with temp_path.open("wb") as output:
        writer.write(output)

    temp_path.replace(pdf_path)

    return True


def add_outline_items(writer, outline, pages_count: int, parent=None) -> int:
    added_count = 0

    for item in outline:
        page_number = item["page_number"]

        if page_number >= pages_count:
            continue

        bookmark = writer.add_outline_item(
            item["title"],
            page_number,
            parent=parent,
        )
        added_count += 1
        added_count += add_outline_items(
            writer,
            item.get("children") or [],
            pages_count,
            parent=bookmark,
        )

    return added_count
