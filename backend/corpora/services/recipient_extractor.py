from functools import lru_cache
from contextlib import contextmanager
import importlib.util
import json
import logging
import os
import re
from pathlib import Path

from django.conf import settings


logger = logging.getLogger(__name__)

RECIPIENT_GENRE = "письмо"
RECIPIENT_MODEL_PATH_ENV = "RECIPIENT_GLINER_MODEL_PATH"
GLINER_MODEL_PATH_ENV = "GLINER_MODEL_PATH"
DEFAULT_LABELS = ["person"]
DEFAULT_THRESHOLD = 0.5
TEXT_WORD_LIMIT = 50
TOKENIZER_FILES = ("tokenizer_config.json", "tokenizer.json", "spm.model")
INITIALS_PATTERN = r"(?:[А-ЯЁA-Z]\.\s*-?\s*){1,4}"
RECIPIENT_TITLES = (
    "милостивый государь",
    "милостивая государыня",
    "милостивому государю",
    "милостивой государыне",
    "государыне",
    "государыня",
    "государю",
    "государь",
    "господину",
    "господину моему",
    "рейхсграфу",
    "рейхсграф",
    "графу",
    "граф",
    "князю",
    "князь",
    "барону",
    "барон",
    "академику",
    "профессору",
    "генералу",
)
RECIPIENT_PREFIXES = ("к", "ко")
NON_PERSON_WORDS = {
    "мастер",
    "пунсонщик",
    "типография",
    "правление",
    "литеры",
    "матрица",
    "матриц",
    "заведение",
    "заведения",
    "сестрица",
    "сестрице",
    "сестрицу",
}


def extract_recipient_for_work(work_data: dict) -> str:
    if normalize_text(work_data.get("genre")) != RECIPIENT_GENRE:
        return ""

    if not is_recipient_language(work_data.get("language")):
        return ""

    title_text = build_title_search_text(work_data)
    recipient = extract_recipient(title_text)

    if recipient:
        return recipient[:200]

    text_start = first_words(work_data.get("plain_text", ""), TEXT_WORD_LIMIT)

    return extract_recipient(text_start, require_strong_signal=True)[:200]


def extract_recipient(text: str, require_strong_signal: bool = False) -> str:
    text = normalize_text(text)

    if not text:
        return ""

    model = get_recipient_model()

    if not model:
        return ""

    labels = get_recipient_labels()
    threshold = get_recipient_threshold()
    entities = model.predict_entities(text, labels, threshold=threshold)
    candidates = [extract_entity_text_with_initials(text, entity) for entity in entities]

    return select_recipient_candidate(candidates, require_strong_signal)


def extract_entity_text_with_initials(source_text: str, entity: dict) -> str:
    entity_text = normalize_text(entity.get("text", ""))
    start = entity.get("start")

    if not entity_text or not isinstance(start, int):
        return entity_text

    prefix = source_text[:start]
    initials = re.search(rf"({INITIALS_PATTERN})$", prefix)

    if not initials:
        return entity_text

    return normalize_text(f"{initials.group(0)} {entity_text}")


def select_recipient_candidate(candidates, require_strong_signal: bool = False) -> str:
    for candidate in candidates:
        recipient = normalize_recipient_name(candidate)

        if is_probable_person_name(recipient, require_strong_signal):
            return recipient

    return ""


def normalize_recipient_name(value: str) -> str:
    recipient = normalize_text(value).strip(" ,.;:()[]")

    prefix_pattern = "|".join(re.escape(prefix) for prefix in RECIPIENT_PREFIXES)
    recipient = re.sub(
        rf"^(?:{prefix_pattern})\s+",
        "",
        recipient,
        flags=re.IGNORECASE,
    )

    title_pattern = "|".join(
        re.escape(title)
        for title in sorted(RECIPIENT_TITLES, key=len, reverse=True)
    )
    recipient = re.sub(
        rf"^(?:(?:{title_pattern})\s+)+",
        "",
        recipient,
        flags=re.IGNORECASE,
    )

    recipient = normalize_text(recipient).strip(" ,.;:()[]")
    recipient = normalize_initials(recipient)

    return lemmatize_recipient_name(recipient)


def normalize_initials(value: str) -> str:
    def replace_initials(match):
        initials = re.findall(r"[А-ЯЁA-Z]\.", match.group(0))

        return "".join(initials) + " "

    return re.sub(
        rf"(?<![А-ЯЁA-Z]){INITIALS_PATTERN}(?=[А-ЯЁA-ZА-ЯЁа-яё])",
        replace_initials,
        value,
    ).strip()


def lemmatize_recipient_name(value: str) -> str:
    morph = get_morph_analyzer()

    if not morph:
        return value

    return re.sub(
        r"[А-ЯЁа-яё]+",
        lambda match: lemmatize_name_word(match.group(0), morph, value, match.end()),
        value,
    )


def lemmatize_name_word(word: str, morph, source_text: str = "", word_end: int | None = None) -> str:
    if is_initial_word(word, source_text, word_end):
        return word

    feminine_patronymic = normalize_feminine_patronymic(word)

    if feminine_patronymic:
        return feminine_patronymic

    parsed = morph.parse(word)

    if not parsed:
        return word

    lemma = parsed[0].normal_form

    if not lemma:
        return word

    if word[:1].isupper():
        return lemma[:1].upper() + lemma[1:]

    return lemma


def is_initial_word(word: str, source_text: str, word_end: int | None) -> bool:
    if len(word) != 1 or not word.isupper() or word_end is None:
        return False

    return word_end < len(source_text) and source_text[word_end] == "."


def normalize_feminine_patronymic(word: str) -> str:
    lower_word = word.lower()
    endings = {
        "вна": "вна",
        "вне": "вна",
        "вну": "вна",
        "вной": "вна",
        "ична": "ична",
        "ичне": "ична",
        "ичну": "ична",
        "ичной": "ична",
        "инична": "инична",
        "иничне": "инична",
        "иничну": "инична",
        "иничной": "инична",
    }

    for ending, normal_ending in endings.items():
        if lower_word.endswith(ending):
            normalized = word[:-len(ending)] + normal_ending

            if word[:1].isupper():
                return normalized[:1].upper() + normalized[1:]

            return normalized

    return ""


@lru_cache(maxsize=1)
def get_morph_analyzer():
    if importlib.util.find_spec("pymorphy3") is None:
        return None

    try:
        import pymorphy3

        return pymorphy3.MorphAnalyzer()
    except Exception:
        logger.exception("Could not initialize pymorphy3 recipient lemmatizer")
        return None


def is_probable_person_name(value: str, require_strong_signal: bool = False) -> bool:
    value = normalize_text(value)

    if not value:
        return False

    words = {word.lower().strip(" ,.;:()[]") for word in value.split()}

    if words & NON_PERSON_WORDS:
        return False

    has_initials = bool(re.search(rf"(?:^|\s){INITIALS_PATTERN}", value))
    capitalized_words = re.findall(r"\b[А-ЯЁA-Z][а-яёa-z]+\.?\b", value)
    has_name_word = bool(capitalized_words)

    if require_strong_signal:
        return (has_initials and has_name_word) or len(capitalized_words) >= 2

    return has_name_word


def is_recipient_language(language: str) -> bool:
    return normalize_text(language).lower().endswith("ru")


def build_title_search_text(work_data: dict) -> str:
    title_parts = [
        work_data.get("title", ""),
        work_data.get("title_short", ""),
        work_data.get("title_desc", ""),
    ]

    text = normalize_text(next((part for part in title_parts if normalize_text(part)), ""))

    return text


def first_words(text: str, limit: int) -> str:
    return " ".join(normalize_text(text).split()[:limit])


def normalize_text(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def get_recipient_labels():
    configured_labels = os.getenv("RECIPIENT_GLINER_LABELS", "")
    labels = [
        label.strip()
        for label in configured_labels.split(",")
        if label.strip()
    ]

    return labels or DEFAULT_LABELS


def get_recipient_threshold():
    try:
        return float(os.getenv("RECIPIENT_GLINER_THRESHOLD", DEFAULT_THRESHOLD))
    except (TypeError, ValueError):
        return DEFAULT_THRESHOLD


@lru_cache(maxsize=1)
def get_recipient_model():
    model_path = get_recipient_model_path()

    if not model_path:
        return None

    if importlib.util.find_spec("gliner") is None:
        return None

    try:
        resolved_model_path = resolve_recipient_model_path(model_path)
        cache_dir = get_model_cache_dir(model_path)

        if not has_available_tokenizer(resolved_model_path, cache_dir):
            logger.warning(
                "GLiNER recipient model at %s does not include tokenizer files and "
                "the base tokenizer is not cached in %s. Recipient extraction is disabled.",
                resolved_model_path,
                cache_dir,
            )
            return None

        with huggingface_offline_mode():
            from gliner import GLiNER

            return GLiNER.from_pretrained(
                str(resolved_model_path),
                cache_dir=str(cache_dir),
                local_files_only=True,
            )
    except Exception:
        logger.exception("Could not load GLiNER recipient model from %s", model_path)
        return None


def get_recipient_model_path():
    configured_path = (
        os.getenv(RECIPIENT_MODEL_PATH_ENV) or
        os.getenv(GLINER_MODEL_PATH_ENV)
    )

    if not configured_path:
        return None

    model_path = Path(configured_path).expanduser()

    if not model_path.is_absolute():
        model_path = Path(settings.BASE_DIR).parent / model_path

    return model_path


def resolve_recipient_model_path(model_path: Path) -> Path:
    if has_model_config(model_path):
        return model_path

    snapshots_path = model_path / "snapshots"

    if not snapshots_path.is_dir():
        return model_path

    ref_path = model_path / "refs" / "main"

    if ref_path.is_file():
        snapshot_hash = ref_path.read_text(encoding="utf-8").strip()
        snapshot_path = snapshots_path / snapshot_hash

        if has_model_config(snapshot_path):
            return snapshot_path

    snapshots = [
        path
        for path in snapshots_path.iterdir()
        if path.is_dir() and has_model_config(path)
    ]

    if not snapshots:
        return model_path

    return max(snapshots, key=lambda path: path.stat().st_mtime)


def has_model_config(path: Path) -> bool:
    return (path / "config.json").is_file() or (path / "gliner_config.json").is_file()


def has_available_tokenizer(model_path: Path, cache_dir: Path) -> bool:
    if has_tokenizer_files(model_path):
        return True

    base_model_name = get_base_model_name(model_path)

    if not base_model_name:
        return False

    cached_model_path = cache_dir / f"models--{base_model_name.replace('/', '--')}"

    return any(
        has_tokenizer_files(snapshot_path)
        for snapshot_path in (cached_model_path / "snapshots").glob("*")
        if snapshot_path.is_dir()
    )


def has_tokenizer_files(path: Path) -> bool:
    return any((path / file_name).is_file() for file_name in TOKENIZER_FILES)


def get_base_model_name(model_path: Path) -> str:
    config_path = model_path / "gliner_config.json"

    if not config_path.is_file():
        return ""

    try:
        return json.loads(config_path.read_text(encoding="utf-8")).get("model_name", "")
    except (OSError, json.JSONDecodeError):
        return ""


def get_model_cache_dir(model_path: Path) -> Path:
    if model_path.name.startswith("models--"):
        return model_path.parent

    return model_path.parent


@contextmanager
def huggingface_offline_mode():
    env_names = ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE")
    old_values = {name: os.environ.get(name) for name in env_names}

    try:
        for name in env_names:
            os.environ[name] = "1"

        yield
    finally:
        for name, value in old_values.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
