from django.test import SimpleTestCase

from .services.text_segments import split_text_into_word_segments


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
