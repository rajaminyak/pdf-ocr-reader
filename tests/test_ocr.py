import fitz

from pdf_ocr_reader.ocr import OCR_DPI, ocr_image


def _rendered_text_png(text: str, dpi: int = OCR_DPI) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), text, fontsize=24)
    png = page.get_pixmap(dpi=dpi).tobytes("png")
    doc.close()
    return png


def test_ocr_reads_text_and_returns_a_sane_bbox():
    png = _rendered_text_png("REACTOR BUNDLE 37R101B corrosion found")
    spans = ocr_image(png)

    joined = " ".join(s.text for s in spans).upper()
    assert "REACTOR" in joined and "CORROSION" in joined
    for s in spans:
        x0, y0, x1, y1 = s.bbox
        assert x1 > x0 and y1 > y0


def test_ocr_blank_image_returns_empty_list():
    doc = fitz.open()
    doc.new_page()
    png = doc[0].get_pixmap(dpi=OCR_DPI).tobytes("png")
    doc.close()
    assert ocr_image(png) == []
