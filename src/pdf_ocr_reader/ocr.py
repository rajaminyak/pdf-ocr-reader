from __future__ import annotations

from pdf_ocr_reader.models import Span

OCR_DPI = 300

_engine = None


class OcrError(Exception):
    pass


def _get_engine():
    global _engine
    if _engine is None:
        from rapidocr import RapidOCR

        _engine = RapidOCR()
    return _engine


def ocr_image(png_bytes: bytes) -> list[Span]:
    engine = _get_engine()
    try:
        result = engine(png_bytes)
    except Exception as exc:  # noqa: BLE001 - engine failure, surface as OcrError
        raise OcrError(str(exc)) from exc

    if result is None or not result.txts:
        return []

    spans: list[Span] = []
    for text, box in zip(result.txts, result.boxes):
        if not text or not text.strip():
            continue
        xs = [float(p[0]) for p in box]
        ys = [float(p[1]) for p in box]
        spans.append(Span(text=text, bbox=(min(xs), min(ys), max(xs), max(ys))))
    return spans
