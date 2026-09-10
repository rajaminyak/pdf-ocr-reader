from __future__ import annotations

from pdf_ocr_reader.document import Document
from pdf_ocr_reader.models import PageHit


def _snippet(text: str, term: str, width: int) -> str:
    lowered = text.lower()
    pos = lowered.find(term)
    if pos == -1:
        return text[:width] + ("..." if len(text) > width else "")
    start = max(0, pos - width // 3)
    end = min(len(text), start + width)
    piece = text[start:end]
    return ("..." if start > 0 else "") + piece + ("..." if end < len(text) else "")


def search(doc: Document, query: str, *, snippet_chars: int = 160, ocr: bool = True) -> list[PageHit]:
    terms = [t for t in query.lower().split() if t]
    if not terms:
        return []

    hits: list[tuple[int, int, PageHit]] = []  # (-score, page_index, hit)
    for page_index in range(doc.page_count):
        spans = doc.page_spans(page_index, ocr=ocr)
        text = " ".join(s.text for s in spans)
        lowered = text.lower()
        if not all(term in lowered for term in terms):
            continue
        score = sum(lowered.count(term) for term in terms)
        boxes = [s.bbox for s in spans if any(term in s.text.lower() for term in terms)]
        hit = PageHit(
            page_index=page_index,
            snippet=_snippet(text, terms[0], snippet_chars),
            span_bboxes=boxes,
        )
        hits.append((-score, page_index, hit))

    hits.sort(key=lambda t: (t[0], t[1]))
    return [h for _, _, h in hits]
