DEFAULT_MIN_SEGMENT_SIZE = 60
DEFAULT_MAX_SEGMENT_SIZE = 120

CLOSING_PUNCTUATION = "\"'”’»)]"


def split_text_into_word_segments(
    text: str,
    min_segment_size: int = DEFAULT_MIN_SEGMENT_SIZE,
    max_segment_size: int = DEFAULT_MAX_SEGMENT_SIZE,
):
    words = text.split()
    fragments = []

    if not words:
        return fragments

    if min_segment_size < 1:
        raise ValueError("min_segment_size должен быть больше 0")

    if max_segment_size < min_segment_size:
        raise ValueError("max_segment_size должен быть не меньше min_segment_size")

    start = 0
    segment_index = 0

    while start < len(words):
        remaining_words = len(words) - start

        if remaining_words <= max_segment_size:
            end = len(words)
        else:
            min_end = start + min_segment_size
            max_end = start + max_segment_size
            end = find_sentence_end(words, min_end, max_end) or max_end

        fragments.append({
            "segment_index": segment_index,
            "word_start": start,
            "word_end": end,
            "text": " ".join(words[start:end]),
        })

        start = end
        segment_index += 1

    return fragments


def split_text_into_sliding_word_segments(text: str, segment_size: int, window_step: int):
    words = text.split()
    fragments = []

    if not words:
        return fragments

    if segment_size < 1:
        raise ValueError("segment_size должен быть больше 0")

    if window_step < 1:
        raise ValueError("window_step должен быть больше 0")

    start = 0
    segment_index = 0

    while start < len(words):
        end = min(start + segment_size, len(words))

        fragments.append({
            "segment_index": segment_index,
            "word_start": start,
            "word_end": end,
            "text": " ".join(words[start:end]),
        })

        if end == len(words):
            break

        start += window_step
        segment_index += 1

    return fragments


def find_sentence_end(words, min_end: int, max_end: int):
    for end in range(min_end, max_end + 1):
        if is_sentence_end(words[end - 1]):
            return end

    return None


def is_sentence_end(word: str):
    stripped_word = word.rstrip(CLOSING_PUNCTUATION)

    if stripped_word.endswith(("!", "?", "…")):
        return True

    if not stripped_word.endswith("."):
        return False

    word_before_period = stripped_word[:-1]

    # Do not split after initials and obvious short abbreviations such as "Я.Я." or "г.".
    return len(word_before_period) > 1 and "." not in word_before_period
