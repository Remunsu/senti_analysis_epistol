from functools import lru_cache
import importlib.util
import os
from pathlib import Path

from django.conf import settings
from transformers import pipeline


MODEL_REPOSITORY_DIR = "models--blanchefort--rubert-base-cased-sentiment-rusentiment"
MODEL_DISPLAY_NAME = "blanchefort/rubert-base-cased-sentiment-rusentiment"

LABEL_TO_POLARITY = {
    "NEGATIVE": "-1",
    "NEUTRAL": "0",
    "POSITIVE": "1",
}


def get_model_path() -> Path:
    configured_path = os.getenv("SENTIMENT_MODEL_PATH")
    repo_root = Path(settings.BASE_DIR).parent

    if configured_path:
        return resolve_model_path(Path(configured_path), repo_root)

    default_candidates = [
        repo_root / "models" / MODEL_REPOSITORY_DIR,
        Path.home() / ".cache" / "huggingface" / "hub" / MODEL_REPOSITORY_DIR,
    ]

    for candidate in default_candidates:
        try:
            return resolve_model_path(candidate, repo_root)
        except FileNotFoundError:
            continue

    searched_paths = "\n".join(str(path) for path in default_candidates)

    raise FileNotFoundError(
        "Не найдена локальная RuBERT-модель. "
        "Скопируйте папку модели в repo_root/models или укажите SENTIMENT_MODEL_PATH в .env. "
        f"Проверенные пути:\n{searched_paths}"
    )


def resolve_model_path(path: Path, repo_root: Path) -> Path:
    model_path = path.expanduser()

    if not model_path.is_absolute():
        model_path = repo_root / model_path

    if (model_path / "config.json").exists():
        return model_path

    snapshots_dir = model_path / "snapshots"

    if not snapshots_dir.exists():
        snapshots_dir = model_path / MODEL_REPOSITORY_DIR / "snapshots"

    if not snapshots_dir.exists():
        raise FileNotFoundError(f"Не найдена папка snapshots в {model_path}")

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
