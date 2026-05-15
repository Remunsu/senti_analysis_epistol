from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings
from django.test import SimpleTestCase
from lxml import etree

from .api import build_sentiment_comparison_rows, delete_volume_and_files
from .services.sentiment_analyzer import get_model_display_name
from .services.tei_parser import extract_work_data, format_pages
from .services.text_segments import split_text_into_word_segments
from .tasks import build_work_snapshot, split_work_text


class TextSegmentTests(SimpleTestCase):
    def test_split_text_after_sentence_end_past_minimum(self):
        text = " ".join([
            "word1",
            "word2",
            "word3",
            "word4",
            "word5.",
            "word6",
            "word7",
            "word8",
            "word9",
            "word10",
            "word11.",
        ])

        fragments = split_text_into_word_segments(text, min_segment_size=4, max_segment_size=7)

        self.assertEqual(
            fragments,
            [
                {
                    "segment_index": 0,
                    "word_start": 0,
                    "word_end": 5,
                    "text": "word1 word2 word3 word4 word5.",
                },
                {
                    "segment_index": 1,
                    "word_start": 5,
                    "word_end": 11,
                    "text": "word6 word7 word8 word9 word10 word11.",
                },
            ],
        )

    def test_split_text_at_maximum_without_sentence_end(self):
        text = " ".join(f"word{index}" for index in range(1, 10))

        fragments = split_text_into_word_segments(text, min_segment_size=4, max_segment_size=6)

        self.assertEqual(
            fragments,
            [
                {
                    "segment_index": 0,
                    "word_start": 0,
                    "word_end": 6,
                    "text": "word1 word2 word3 word4 word5 word6",
                },
                {
                    "segment_index": 1,
                    "word_start": 6,
                    "word_end": 9,
                    "text": "word7 word8 word9",
                },
            ],
        )

    def test_initials_do_not_end_sentence(self):
        text = " ".join([
            "word1",
            "word2",
            "word3",
            "Я.Я.",
            "word5",
            "word6.",
            "word7",
            "word8",
        ])

        fragments = split_text_into_word_segments(text, min_segment_size=4, max_segment_size=7)

        self.assertEqual(fragments[0]["word_end"], 6)
        self.assertEqual(fragments[0]["text"], "word1 word2 word3 Я.Я. word5 word6.")


class TeiParserTests(SimpleTestCase):
    def test_extract_work_data_falls_back_to_header_title(self):
        tei_node = etree.fromstring(
            """
            <TEI xmlns="http://www.tei-c.org/ns/1.0">
              <teiHeader>
                <fileDesc>
                  <titleStmt>
                    <title>1764 сентября 20. Я.Я. Штелину</title>
                  </titleStmt>
                </fileDesc>
              </teiHeader>
              <text>
                <body />
              </text>
            </TEI>
            """.encode()
        )

        work_data = extract_work_data(tei_node, SimpleNamespace(author=""))

        self.assertEqual(work_data["title"], "1764 сентября 20. Я.Я. Штелину")
        self.assertEqual(work_data["title_short"], "1764 сентября 20. Я.Я. Штелину")

    def test_format_pages_compacts_numeric_values(self):
        self.assertEqual(format_pages(["10", "7", "8", "10"]), "7-10")


class AnalysisSnapshotTests(SimpleTestCase):
    def test_build_work_snapshot_captures_result_metadata(self):
        work = SimpleNamespace(
            id=12,
            title="Письмо",
            author="Автор",
            date_from="1764-09-20",
            date_to="1764-09-20",
            genre="письмо",
            place="Петербург",
        )

        self.assertEqual(
            build_work_snapshot(work),
            {
                "original_work_id": 12,
                "snapshot_title": "Письмо",
                "snapshot_author": "Автор",
                "snapshot_date_from": "1764-09-20",
                "snapshot_date_to": "1764-09-20",
                "snapshot_genre": "письмо",
                "snapshot_place": "Петербург",
            },
        )

    def test_split_work_text_keeps_legacy_window_runs_compatible(self):
        run = SimpleNamespace(segment_size=4, max_segment_size=None, window_step=2)

        fragments = split_work_text("one two three four five six", run)

        self.assertEqual([fragment["word_start"] for fragment in fragments], [0, 2])

    def test_build_sentiment_comparison_rows_matches_runs_by_original_work_id(self):
        baseline_summary = [
            {
                "original_work_id": 12,
                "work_id": 12,
                "title": "Письмо",
                "date": "1764-09-20",
                "segments_count": 4,
                "negative_count": 2,
                "neutral_count": 1,
                "positive_count": 1,
                "mean_score": -0.25,
            }
        ]
        candidate_summary = [
            {
                "original_work_id": 12,
                "work_id": 12,
                "title": "Письмо",
                "date": "1764-09-20",
                "segments_count": 2,
                "negative_count": 0,
                "neutral_count": 2,
                "positive_count": 0,
                "mean_score": 0,
            }
        ]

        rows = build_sentiment_comparison_rows(baseline_summary, candidate_summary)

        self.assertEqual(rows[0]["original_work_id"], 12)
        self.assertEqual(rows[0]["baseline"]["segments_count"], 4)
        self.assertEqual(rows[0]["candidate"]["segments_count"], 2)
        self.assertEqual(rows[0]["mean_score_delta"], 0.25)
        self.assertEqual(rows[0]["segments_delta"], -2)


class SentimentAnalyzerTests(SimpleTestCase):
    @override_settings(BASE_DIR=Path("/tmp/project/backend"))
    def test_model_display_name_uses_configured_model_folder(self):
        with patch.dict("os.environ", {"SENTIMENT_MODEL_PATH": "models/my-sentiment-model"}):
            self.assertEqual(get_model_display_name(), "my-sentiment-model")

    @override_settings(BASE_DIR=Path("/tmp/project/backend"))
    def test_model_display_name_requires_configured_model_path(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(FileNotFoundError, "SENTIMENT_MODEL_PATH"):
                get_model_display_name()


class VolumeFileCleanupTests(SimpleTestCase):
    def test_delete_volume_and_files_removes_stored_files(self):
        xml_file = FakeFile()
        pdf_file = FakeFile()
        volume = FakeVolume(xml_file, pdf_file)

        delete_volume_and_files(volume)

        self.assertTrue(volume.deleted)
        self.assertEqual(xml_file.delete_calls, [False])
        self.assertEqual(pdf_file.delete_calls, [False])


class FakeFile:
    def __init__(self):
        self.delete_calls = []

    def __bool__(self):
        return True

    def delete(self, save=False):
        self.delete_calls.append(save)


class FakeVolume:
    def __init__(self, xml_file, pdf_file):
        self.xml_file = xml_file
        self.facsimile_file = pdf_file
        self.deleted = False

    def delete(self):
        self.deleted = True
