import pytest
from PySide6.QtWidgets import QApplication

from pdf_ocr_reader.gui.mainwindow import MainWindow




def test_open_shows_first_page_and_thumbnails(qapp, born_digital_pdf):
    w = MainWindow()
    w.open_pdf(born_digital_pdf, background_ocr=False)
    assert w.page_spin.value() == 1
    assert w.page_spin.maximum() == 2
    assert w.thumbs.count() == 2
    assert w.view._pixmap_item is not None
    w.close()


def test_native_pages_are_immediately_in_spans(qapp, born_digital_pdf):
    w = MainWindow()
    w.open_pdf(born_digital_pdf, background_ocr=False)
    assert any(s.text == "reactor" for s in w._spans.get(0, []))
    w.close()


def test_go_to_page_updates_view_and_spinbox(qapp, born_digital_pdf):
    w = MainWindow()
    w.open_pdf(born_digital_pdf, background_ocr=False)
    w.go_to_page(1)
    assert w.page_spin.value() == 2
    w.go_to_page(99)  # clamps
    assert w.page_spin.value() == 2
    w.close()


def test_search_lists_hits_and_clicking_jumps_and_highlights(qapp, born_digital_pdf):
    w = MainWindow()
    w.open_pdf(born_digital_pdf, background_ocr=False)
    w.run_search("monitoring")
    assert w.results.count() == 1
    w._open_result(w.results.item(0))
    assert w.page_spin.value() == 2  # "monitoring" is on page 2
    # scene has the pixmap plus at least one highlight rect
    assert len(w.view.scene().items()) >= 2
    w.close()


def test_blank_search_hides_results_and_clears_highlights(qapp, born_digital_pdf):
    w = MainWindow()
    w.open_pdf(born_digital_pdf, background_ocr=False)
    w.run_search("reactor")
    assert not w.results.isHidden()
    w.run_search("")
    assert w.results.isHidden()
    w.close()


def test_clear_cache_menu_reports_count(qapp, scanned_pdf, monkeypatch):
    from pdf_ocr_reader import cache
    from pdf_ocr_reader.document import Document

    with Document.open(scanned_pdf) as doc:
        doc.page_spans(0)  # seed one cache entry

    seen = {}
    monkeypatch.setattr(
        "pdf_ocr_reader.gui.mainwindow.QMessageBox.information",
        lambda *a, **k: seen.setdefault("msg", a[-1]),
    )
    w = MainWindow()
    w._clear_cache()
    assert "1 cached document" in seen["msg"]
    assert cache.disk_usage() == 0
    w.close()


def test_export_searchable_writes_a_file(qapp, scanned_pdf, tmp_path):
    w = MainWindow()
    w.open_pdf(scanned_pdf, background_ocr=False)
    out = tmp_path / "copy.pdf"
    w.export_searchable(str(out))
    assert out.is_file()

    import fitz

    d = fitz.open(str(out))
    got = d[0].get_text().lower()
    d.close()
    assert "turbine" in got or "bearing" in got
    w.close()


def test_save_action_enabled_after_open(qapp, born_digital_pdf):
    w = MainWindow()
    assert not w.save_action.isEnabled()
    w.open_pdf(born_digital_pdf, background_ocr=False)
    assert w.save_action.isEnabled()
    w.close()
