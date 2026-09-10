from __future__ import annotations

import re

import fitz

from pdf_ocr_reader.models import Span

MIN_NATIVE_CHARS = 12
MIN_REAL_WORDS = 3

_WORD_RE = re.compile(r"[^\W\d_]{4,}", re.UNICODE)  # runs of 4+ letters
_VOWELS = set("aeiouAEIOUàáâäèéêëìíîïòóôöùúûü")


def _real_words(text: str) -> list[str]:
    """Letter-runs of 4+ chars that contain a vowel — a decent 'this is prose' signal.

    Some PDFs carry a broken 'text layer': a custom-encoded font with no
    ToUnicode map, so `get_text()` returns punctuation and short letter
    fragments, not words. Those pages must be treated as image-only (OCR
    candidates), not as searchable.
    """
    return [w for w in _WORD_RE.findall(text) if any(c in _VOWELS for c in w)]


def _is_readable(text: str) -> bool:
    if len(text) < MIN_NATIVE_CHARS:
        return False
    words = _real_words(text)
    return len(words) >= MIN_REAL_WORDS and sum(len(w) for w in words) / len(text) >= 0.2


def native_page_spans(page: fitz.Page) -> list[Span] | None:
    words = page.get_text("words")  # (x0, y0, x1, y1, "word", block, line, word_no)
    joined = " ".join(w[4] for w in words)
    if not _is_readable(joined):
        return None
    return [
        Span(text=w[4], bbox=(float(w[0]), float(w[1]), float(w[2]), float(w[3])))
        for w in words
        if w[4].strip()
    ]
