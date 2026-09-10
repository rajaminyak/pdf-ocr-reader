import pytest

from pdf_ocr_reader.document import Document, DocumentError


def test_open_reports_page_count_and_stable_hash(born_digital_pdf):
    with Document.open(born_digital_pdf) as doc:
        assert doc.page_count == 2
        h1 = doc.content_hash
    with Document.open(born_digital_pdf) as doc:
        assert doc.content_hash == h1
    assert len(h1) == 64


def test_page_spans_and_text_from_born_digital(born_digital_pdf):
    with Document.open(born_digital_pdf) as doc:
        assert doc.has_text_layer(0) is True
        assert "37-R-101B" in doc.full_page_text(0)
        assert any(s.text == "reactor" for s in doc.page_spans(0))


def test_image_only_page_has_no_text_layer_and_empty_spans(scanned_pdf):
    with Document.open(scanned_pdf) as doc:
        assert doc.has_text_layer(0) is False
        assert doc.page_spans(0) == []
        assert doc.full_page_text(0) == ""


def test_corrupt_file_raises_document_error(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf at all")
    with pytest.raises(DocumentError):
        Document.open(str(bad))
