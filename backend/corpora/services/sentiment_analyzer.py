from functools import lru_cache
import importlib.util
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
    snapshots_dir = Path(settings.BASE_DIR).parent / "models" / MODEL_REPOSITORY_DIR / "snapshots"
    snapshots = sorted(snapshots_dir.iterdir())

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


def split_text_into_word_segments(text: str, segment_size: int = 50):
    words = text.split()
    fragments = []

    for segment_index, start in enumerate(range(0, len(words), segment_size)):
        end = min(start + segment_size, len(words))

        fragments.append({
            "segment_index": segment_index,
            "word_start": start,
            "word_end": end,
            "text": " ".join(words[start:end]),
        })

    return fragments


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
