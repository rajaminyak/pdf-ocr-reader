import pytest
from PySide6.QtWidgets import QApplication

from pdf_ocr_reader.gui.pageview import PageGraphicsView, scene_rect_for_span




def test_native_span_scales_from_points_to_render_dpi():
    x, y, w, h = scene_rect_for_span((72.0, 36.0, 144.0, 48.0), source_dpi=72, render_dpi=150)
    assert round(x) == 150 and round(y) == 75
    assert round(w) == 150 and round(h) == 25


def test_ocr_span_scales_from_ocr_dpi_to_render_dpi():
    x, y, w, h = scene_rect_for_span((300.0, 600.0, 900.0, 660.0), source_dpi=300, render_dpi=150)
    assert (round(x), round(y), round(w), round(h)) == (150, 300, 300, 30)


def test_show_page_and_highlights_do_not_raise(qapp, born_digital_pdf):
    import fitz

    from pdf_ocr_reader.renderer import render_page

    doc = fitz.open(born_digital_pdf)
    png = render_page(doc[0], dpi=150).png_bytes
    doc.close()

    view = PageGraphicsView()
    view.show_page(png)
    view.set_highlights([(10.0, 10.0, 50.0, 12.0)])
    assert view.scene().items()
