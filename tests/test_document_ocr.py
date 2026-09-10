from unittest.mock import patch

from pdf_ocr_reader.document import Document


def test_scanned_page_is_searchable_after_ocr(scanned_pdf, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    with Document.open(scanned_pdf) as doc:
        spans = doc.page_spans(0)
    joined = " ".join(s.text for s in spans).lower()
    assert "turbine" in joined or "bearing" in joined


def test_second_open_uses_cache_and_does_not_re_ocr(scanned_pdf, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    with Document.open(scanned_pdf) as doc:
        doc.page_spans(0)  # first OCR + persist

    with patch("pdf_ocr_reader.document.ocr.ocr_image", side_effect=AssertionError("re-OCR!")):
        with Document.open(scanned_pdf) as doc:
            spans = doc.page_spans(0)
    assert spans and any(s.text for s in spans)


def test_ocr_all_reports_progress(scanned_pdf, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    events = []
    with Document.open(scanned_pdf) as doc:
        doc.ocr_all(progress=lambda done, total: events.append((done, total)))
    assert events == [(1, 1)]


def test_native_page_never_triggers_ocr(born_digital_pdf, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    with patch("pdf_ocr_reader.document.ocr.ocr_image", side_effect=AssertionError("should not OCR")):
        with Document.open(born_digital_pdf) as doc:
            assert "reactor" in doc.full_page_text(0).lower()
            doc.ocr_all()


def test_failed_ocr_page_returns_empty_and_is_not_retried(scanned_pdf, tmp_path, monkeypatch):
    from pdf_ocr_reader.ocr import OcrError

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    calls = []

    def boom(png):
        calls.append(1)
        raise OcrError("engine exploded")

    with patch("pdf_ocr_reader.document.ocr.ocr_image", side_effect=boom):
        with Document.open(scanned_pdf) as doc:
            assert doc.page_spans(0) == []
            assert doc.page_spans(0) == []  # served from the in-memory store
    assert len(calls) == 1
