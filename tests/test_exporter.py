import fitz
import pytest

from pdf_ocr_reader.document import Document
from pdf_ocr_reader.exporter import ExportError, save_searchable_pdf


def test_export_adds_a_searchable_layer_to_a_scanned_pdf(scanned_pdf, tmp_path):
    out = tmp_path / "scan (searchable).pdf"
    with Document.open(scanned_pdf) as doc:
        doc.ocr_all()
        save_searchable_pdf(doc, str(out))

    result = fitz.open(str(out))
    text = result[0].get_text().lower()
    result.close()
    assert "turbine" in text or "bearing" in text

    src = fitz.open(scanned_pdf)
    assert len(src[0].get_text().strip()) < 12
    src.close()


def test_export_keeps_a_born_digital_pdf_readable(born_digital_pdf, tmp_path):
    out = tmp_path / "born (searchable).pdf"
    with Document.open(born_digital_pdf) as doc:
        doc.ocr_all()
        save_searchable_pdf(doc, str(out))
    result = fitz.open(str(out))
    assert "reactor" in result[0].get_text().lower()
    result.close()


def test_export_refuses_to_overwrite_the_source(scanned_pdf):
    with Document.open(scanned_pdf) as doc:
        with pytest.raises(ExportError):
            save_searchable_pdf(doc, scanned_pdf)
