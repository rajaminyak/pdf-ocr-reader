import fitz

from pdf_ocr_reader.textlayer import _is_readable, native_page_spans


def test_is_readable_accepts_prose_rejects_control_chars():
    assert _is_readable("Inspection report for the 37-R-101B reactor bundle")
    assert not _is_readable("\x00\x01\x02\x03\x04\x05\x06\x07\x08\x01\n\x04\x03\x08\x0b\x06")


def test_native_spans_from_born_digital_page(born_digital_pdf):
    doc = fitz.open(born_digital_pdf)
    spans = native_page_spans(doc[0])
    doc.close()

    assert spans is not None
    words = [s.text for s in spans]
    assert "37-R-101B" in words
    assert "reactor" in words
    for s in spans:
        x0, y0, x1, y1 = s.bbox
        assert x1 > x0 and y1 > y0


def test_native_spans_none_for_image_only_page(scanned_pdf):
    doc = fitz.open(scanned_pdf)
    spans = native_page_spans(doc[0])
    doc.close()
    assert spans is None
