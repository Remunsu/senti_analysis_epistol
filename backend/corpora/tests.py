from types import SimpleNamespace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import override_settings
from django.test import SimpleTestCase
from lxml import etree

from .api import SentimentSummaryMixin, WorkFilterMixin, delete_volume_and_files
from .services.sentiment_analyzer import get_model_display_name, map_prediction_label
from .services.recipient_extractor import (
    extract_recipient_for_work,
    extract_entity_text_with_initials,
    get_recipient_model_path,
    is_recipient_language,
    lemmatize_recipient_name,
    normalize_initials,
    normalize_recipient_name,
    resolve_recipient_model_path,
    select_recipient_candidate,
)
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
            recipient="Адресат",
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
                "snapshot_recipient": "Адресат",
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

    def test_extract_year_uses_date_to_only(self):
        summary = SentimentSummaryMixin()

        self.assertEqual(summary.extract_year_from_date_to("1751/1752"), "1751")
        self.assertEqual(summary.extract_year_from_date_to(""), "")


class WorkFilterTests(SimpleTestCase):
    def test_volume_filter_discards_non_numeric_values(self):
        filters = WorkFilterMixin()

        self.assertEqual(filters.clean_filter_values(["ЛМН. ПСС, 11", "11"], numeric=True), ["11"])


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

    def test_label_mapping_supports_lowercase_labels(self):
        self.assertEqual(map_prediction_label("negative"), "-1")
        self.assertEqual(map_prediction_label("neutral"), "0")
        self.assertEqual(map_prediction_label("positive"), "1")


class RecipientExtractorTests(SimpleTestCase):
    def test_extract_recipient_for_work_uses_title_for_letters(self):
        fake_model = FakeRecipientModel([{"start": 22, "end": 29, "text": "Штелину"}])

        with patch("corpora.services.recipient_extractor.get_recipient_model", return_value=fake_model):
            recipient = extract_recipient_for_work({
                "genre": "письмо",
                "language": "ru",
                "title": "1764 сентября 20. Я.Я. Штелину",
                "title_short": "",
                "title_desc": "",
                "plain_text": "Милостивый государь.",
            })

        self.assertEqual(recipient, "Я.Я. Штелин")
        self.assertEqual(fake_model.searched_texts, ["1764 сентября 20. Я.Я. Штелину"])

    def test_entity_text_expands_previous_initials(self):
        self.assertEqual(
            extract_entity_text_with_initials(
                "1757 октября 27. Я.Я. Штелину",
                {"start": 22, "end": 29, "text": "Штелину"},
            ),
            "Я.Я. Штелину",
        )

    def test_entity_text_expands_spaced_previous_initials(self):
        self.assertEqual(
            extract_entity_text_with_initials(
                "1757 октября 27. Я. Я. Штелину",
                {"start": 23, "end": 30, "text": "Штелину"},
            ),
            "Я. Я. Штелину",
        )

    def test_entity_text_expands_hyphenated_previous_initials(self):
        self.assertEqual(
            extract_entity_text_with_initials(
                '1757. И.-А. Корфу "Великие милости"',
                {"start": 11, "end": 16, "text": "Корфу"},
            ),
            "И.-А. Корфу",
        )

    def test_select_recipient_candidate_rejects_initials_without_name(self):
        self.assertEqual(select_recipient_candidate(["Я. Я"]), "")

    def test_extract_recipient_for_work_skips_non_letters(self):
        fake_model = FakeRecipientModel([{"text": "Я.Я. Штелину"}])

        with patch("corpora.services.recipient_extractor.get_recipient_model", return_value=fake_model):
            recipient = extract_recipient_for_work({
                "genre": "проза",
                "language": "ru",
                "title": "1764 сентября 20. Я.Я. Штелину",
                "plain_text": "",
            })

        self.assertEqual(recipient, "")
        self.assertEqual(fake_model.searched_texts, [])

    def test_extract_recipient_for_work_skips_languages_not_ending_with_ru(self):
        fake_model = FakeRecipientModel([{"text": "Я.Я. Штелину"}])

        with patch("corpora.services.recipient_extractor.get_recipient_model", return_value=fake_model):
            recipient = extract_recipient_for_work({
                "genre": "письмо",
                "language": "de",
                "title": "1764 сентября 20. Я.Я. Штелину",
                "plain_text": "",
            })

        self.assertEqual(recipient, "")
        self.assertEqual(fake_model.searched_texts, [])

    def test_recipient_language_accepts_values_ending_with_ru(self):
        self.assertTrue(is_recipient_language("ru"))
        self.assertTrue(is_recipient_language("de ru"))
        self.assertTrue(is_recipient_language("la ru"))
        self.assertFalse(is_recipient_language("de"))

    def test_text_fallback_rejects_role_like_candidate(self):
        self.assertEqual(
            select_recipient_candidate(["Словолитный мастер"], require_strong_signal=True),
            "",
        )

    def test_text_fallback_keeps_full_person_name(self):
        self.assertEqual(
            select_recipient_candidate(["Михайло Ларионович"], require_strong_signal=True),
            "Михайло Ларионович",
        )

    def test_select_recipient_candidate_skips_salutation_phrase(self):
        fake_morph = FakeMorphAnalyzer({
            "моя": "мой",
            "сестрица": "сестрица",
            "Марья": "марья",
        })

        with patch("corpora.services.recipient_extractor.get_morph_analyzer", return_value=fake_morph):
            self.assertEqual(
                select_recipient_candidate(["Государыня моя сестрица", "Марья Васильевна"]),
                "Марья Васильевна",
            )

    def test_normalize_recipient_name_strips_titles(self):
        self.assertEqual(
            normalize_recipient_name("рейхсграф Михайло Ларионович"),
            "Михайло Ларионович",
        )

    def test_normalize_recipient_name_strips_polite_salutation(self):
        self.assertEqual(
            normalize_recipient_name("Милостивый государь Иван Иванович"),
            "Иван Иванович",
        )

    def test_normalize_recipient_name_strips_direction_prefix(self):
        self.assertEqual(
            normalize_recipient_name("к И.И. Шувалову"),
            "И.И. Шувалов",
        )

    def test_normalize_initials_removes_spaces_and_hyphens(self):
        self.assertEqual(normalize_initials("Я. Я. Штелин"), "Я.Я. Штелин")
        self.assertEqual(normalize_initials("И.-А. Корф"), "И.А. Корф")

    def test_lemmatize_recipient_name_normalizes_russian_words(self):
        fake_morph = FakeMorphAnalyzer({
            "Д": "далее",
            "Виноградову": "виноградов",
            "Формею": "формей",
            "Марье": "марья",
            "Михайлу": "михайло",
            "Ларионовичу": "ларионович",
        })

        with patch("corpora.services.recipient_extractor.get_morph_analyzer", return_value=fake_morph):
            self.assertEqual(
                lemmatize_recipient_name("Д.И. Виноградову"),
                "Д.И. Виноградов",
            )
            self.assertEqual(
                lemmatize_recipient_name("И.И. Формею"),
                "И.И. Формей",
            )
            self.assertEqual(
                lemmatize_recipient_name("Михайлу Ларионовичу"),
                "Михайло Ларионович",
            )
            self.assertEqual(
                lemmatize_recipient_name("Марье Васильевне"),
                "Марья Васильевна",
            )

    def test_recipient_model_path_resolves_huggingface_cache_snapshot(self):
        with self.settings(BASE_DIR=Path("/tmp/project/backend")):
            with patch.dict("os.environ", {"RECIPIENT_GLINER_MODEL_PATH": "models--test--gliner"}):
                self.assertEqual(
                    get_recipient_model_path(),
                    Path("/tmp/project/models--test--gliner"),
                )

    def test_resolve_recipient_model_path_uses_main_snapshot(self):
        with TemporaryDirectory() as tmp_dir:
            model_path = Path(tmp_dir) / "models--urchade--gliner"
            snapshot_path = model_path / "snapshots" / "abc123"
            refs_path = model_path / "refs"
            snapshot_path.mkdir(parents=True)
            refs_path.mkdir()
            (refs_path / "main").write_text("abc123", encoding="utf-8")
            (snapshot_path / "gliner_config.json").write_text("{}", encoding="utf-8")

            self.assertEqual(resolve_recipient_model_path(model_path), snapshot_path)


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


class FakeRecipientModel:
    def __init__(self, entities):
        self.entities = entities
        self.searched_texts = []

    def predict_entities(self, text, labels, threshold=0.5):
        self.searched_texts.append(text)
        return self.entities


class FakeMorphParse:
    def __init__(self, normal_form):
        self.normal_form = normal_form


class FakeMorphAnalyzer:
    def __init__(self, normal_forms):
        self.normal_forms = normal_forms

    def parse(self, word):
        return [FakeMorphParse(self.normal_forms.get(word, word.lower()))]
