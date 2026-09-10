from __future__ import annotations

from pdf_ocr_reader.document import Document
from pdf_ocr_reader.models import PageHit, Span


def _snippet(text: str, term: str, width: int) -> str:
    lowered = text.lower()
    pos = lowered.find(term)
    if pos == -1:
        return text[:width] + ("..." if len(text) > width else "")
    start = max(0, pos - width // 3)
    end = min(len(text), start + width)
    piece = text[start:end]
    return ("..." if start > 0 else "") + piece + ("..." if end < len(text) else "")


def search_spans(
    spans_by_page: dict[int, list[Span]], query: str, *, snippet_chars: int = 160
) -> list[PageHit]:
    terms = [t for t in query.lower().split() if t]
    if not terms:
        return []

    hits: list[tuple[int, int, PageHit]] = []  # (-score, page_index, hit)
    for page_index, spans in spans_by_page.items():
        text = " ".join(s.text for s in spans)
        lowered = text.lower()
        if not all(term in lowered for term in terms):
            continue
        score = sum(lowered.count(term) for term in terms)
        boxes = [s.bbox for s in spans if any(term in s.text.lower() for term in terms)]
        hits.append(
            (-score, page_index, PageHit(page_index, _snippet(text, terms[0], snippet_chars), boxes))
        )

    hits.sort(key=lambda t: (t[0], t[1]))
    return [h for _, _, h in hits]


def search(
    doc: Document, query: str, *, snippet_chars: int = 160, ocr: bool = True
) -> list[PageHit]:
    spans_by_page = {i: doc.page_spans(i, ocr=ocr) for i in range(doc.page_count)}
    return search_spans(spans_by_page, query, snippet_chars=snippet_chars)
