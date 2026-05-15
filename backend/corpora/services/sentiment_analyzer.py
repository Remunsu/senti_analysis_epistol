from functools import lru_cache
import importlib.util
import os
from pathlib import Path

from django.conf import settings
from transformers import pipeline

LABEL_TO_POLARITY = {
    "NEGATIVE": "-1",
    "NEUTRAL": "0",
    "POSITIVE": "1",
}


def get_model_path() -> Path:
    model_source_path, repo_root = get_model_source_path()

    return resolve_model_path(model_source_path, repo_root)


def get_model_display_name() -> str:
    model_source_path, _ = get_model_source_path()

    return model_source_path.name


def get_model_source_path():
    configured_path = os.getenv("SENTIMENT_MODEL_PATH")
    repo_root = Path(settings.BASE_DIR).parent

    if not configured_path:
        raise FileNotFoundError(
            "Не задан SENTIMENT_MODEL_PATH в .env. "
            "Укажите путь к локальной папке модели."
        )

    return normalize_model_path(Path(configured_path), repo_root), repo_root


def normalize_model_path(path: Path, repo_root: Path) -> Path:
    model_path = path.expanduser()

    if not model_path.is_absolute():
        model_path = repo_root / model_path

    return model_path


def resolve_model_path(path: Path, repo_root: Path) -> Path:
    model_path = normalize_model_path(path, repo_root)

    if (model_path / "config.json").exists():
        return model_path

    snapshots_dir = model_path / "snapshots"

    if not snapshots_dir.exists():
        raise FileNotFoundError(
            f"В {model_path} не найден config.json или папка snapshots"
        )

    snapshots = sorted(
        snapshot for snapshot in snapshots_dir.iterdir()
        if snapshot.is_dir() and (snapshot / "config.json").exists()
    )

    if not snapshots:
        raise FileNotFoundError(f"Не найдена локальная модель в {snapshots_dir}")

    return snapshots[-1]


@lru_cache(maxsize=1)
def get_classifier():
    if importlib.util.find_spec("torch") is None:
        raise RuntimeError("Для анализа RuBERT нужно установить PyTorch: pip install torch")

    model_path = get_model_path()

    return pipeline(
        "text-classification",
        model=str(model_path),
        tokenizer=str(model_path),
    )


def analyze_fragments(fragments):
    if not fragments:
        return []

    classifier = get_classifier()
    predictions = classifier(
        [fragment["text"] for fragment in fragments],
        batch_size=8,
        truncation=True,
        max_length=512,
    )

    results = []

    for fragment, prediction in zip(fragments, predictions):
        label = prediction["label"]

        results.append({
            **fragment,
            "label": LABEL_TO_POLARITY.get(label, "0"),
            "confidence": float(prediction["score"]),
        })

    return results
