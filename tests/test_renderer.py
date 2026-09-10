import fitz

from pdf_ocr_reader.renderer import render_page


def test_render_returns_png_bytes_and_dimensions(born_digital_pdf):
    doc = fitz.open(born_digital_pdf)
    r = render_page(doc[0], dpi=150)
    doc.close()
    assert r.png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
    assert r.width > 0 and r.height > 0
    assert r.dpi == 150


def test_higher_dpi_yields_larger_image(born_digital_pdf):
    doc = fitz.open(born_digital_pdf)
    small = render_page(doc[0], dpi=72)
    large = render_page(doc[0], dpi=200)
    doc.close()
    assert large.width > small.width and large.height > small.height
