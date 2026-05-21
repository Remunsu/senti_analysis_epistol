from django.db import close_old_connections

from .models import SentimentAnalysisResult, SentimentAnalysisRun, Work
from .services.sentiment_analyzer import analyze_fragments
from .services.text_segments import split_text_into_sliding_word_segments, split_text_into_word_segments


def run_sentiment_analysis(run_id, work_ids, *legacy_segmentation_args):
    close_old_connections()

    try:
        run = SentimentAnalysisRun.objects.get(id=run_id)
        works = (
            Work.objects
            .filter(id__in=work_ids)
            .exclude(plain_text="")
            .only(
                "id",
                "plain_text",
                "title",
                "author",
                "recipient",
                "date_from",
                "date_to",
                "genre",
                "place",
            )
            .order_by("id")
        )
        results_count = 0

        SentimentAnalysisResult.objects.filter(run=run).delete()

        for work in works:
            fragments = split_work_text(work.plain_text, run)
            analysis_results = analyze_fragments(fragments)
            snapshot = build_work_snapshot(work)

            result_objects = [
                SentimentAnalysisResult(
                    run=run,
                    work=work,
                    **snapshot,
                    segment_index=result["segment_index"],
                    word_start=result["word_start"],
                    word_end=result["word_end"],
                    text=result["text"],
                    label=result["label"],
                    confidence=result["confidence"],
                )
                for result in analysis_results
            ]

            SentimentAnalysisResult.objects.bulk_create(result_objects, batch_size=500)
            results_count += len(result_objects)
            SentimentAnalysisRun.objects.filter(id=run.id).update(results_count=results_count)
    except Exception as exc:
        SentimentAnalysisResult.objects.filter(run_id=run_id).delete()
        SentimentAnalysisRun.objects.filter(id=run_id).update(
            status="failed",
            error_message=str(exc) or "Не удалось выполнить анализ",
            results_count=0,
        )
        raise
    else:
        SentimentAnalysisRun.objects.filter(id=run_id).update(
            status="completed",
            results_count=results_count,
            error_message="",
        )
    finally:
        close_old_connections()


def split_work_text(text, run):
    if run.max_segment_size:
        return split_text_into_word_segments(text, run.segment_size, run.max_segment_size)

    legacy_window_step = run.window_step or run.segment_size
    return split_text_into_sliding_word_segments(text, run.segment_size, legacy_window_step)


def build_work_snapshot(work):
    return {
        "original_work_id": work.id,
        "snapshot_title": work.title,
        "snapshot_author": work.author,
        "snapshot_recipient": work.recipient,
        "snapshot_date_from": work.date_from,
        "snapshot_date_to": work.date_to,
        "snapshot_genre": work.genre,
        "snapshot_place": work.place,
    }
