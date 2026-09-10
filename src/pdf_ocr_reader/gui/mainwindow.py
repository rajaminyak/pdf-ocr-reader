from __future__ import annotations

import os

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QIcon, QImage, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from pdf_ocr_reader import cache
from pdf_ocr_reader.document import Document, DocumentError
from pdf_ocr_reader.exporter import ExportError, save_searchable_pdf
from pdf_ocr_reader.gui.config import load_config, save_config
from pdf_ocr_reader.gui.pageview import PageGraphicsView, scene_rect_for_span
from pdf_ocr_reader.gui.worker import OcrWorker, run_in_thread
from pdf_ocr_reader.renderer import render_page
from pdf_ocr_reader.search import search_spans

_THUMB_DPI = 24


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PDF OCR Reader")
        self.resize(1200, 850)
        self.config = load_config()

        self._doc: Document | None = None
        self._worker: OcrWorker | None = None
        self._thread = None
        self._spans: dict[int, list] = {}
        self._page_index = 0
        self._active_query = ""

        self._build_ui()
        self._build_menu()

    # ---------- UI ----------

    def _build_ui(self) -> None:
        bar = QToolBar()
        bar.setMovable(False)
        self.addToolBar(bar)

        open_btn = QPushButton("Open…")
        open_btn.clicked.connect(self._choose_file)
        bar.addWidget(open_btn)
        bar.addSeparator()

        bar.addWidget(QLabel("Page"))
        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(1)
        self.page_spin.valueChanged.connect(lambda v: self.go_to_page(v - 1))
        bar.addWidget(self.page_spin)
        self.page_total = QLabel("of 0")
        bar.addWidget(self.page_total)
        bar.addSeparator()

        for label, factor in (("−", 0.8), ("Fit", None), ("+", 1.25)):
            b = QPushButton(label)
            if factor is None:
                b.clicked.connect(lambda: self.view.fit())
            else:
                b.clicked.connect(lambda _=False, f=factor: self.view.zoom(f))
            bar.addWidget(b)
        bar.addSeparator()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search inside this document…")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.returnPressed.connect(lambda: self.run_search(self.search_box.text()))
        bar.addWidget(self.search_box)

        self.thumbs = QListWidget()
        self.thumbs.setViewMode(QListWidget.IconMode)
        self.thumbs.setIconSize(QSize(120, 160))
        self.thumbs.setFixedWidth(170)
        self.thumbs.setMovement(QListWidget.Static)
        self.thumbs.setSpacing(4)
        self.thumbs.currentRowChanged.connect(self.go_to_page)

        self.view = PageGraphicsView()

        self.results = QListWidget()
        self.results.setFixedWidth(300)
        self.results.itemActivated.connect(self._open_result)
        self.results.itemClicked.connect(self._open_result)
        self.results.hide()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.thumbs)
        splitter.addWidget(self.view)
        splitter.addWidget(self.results)
        splitter.setStretchFactor(1, 1)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter, 1)

        prog_row = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.hide()
        self.status = QLabel("")
        prog_row.addWidget(self.status)
        prog_row.addWidget(self.progress, 1)
        layout.addLayout(prog_row)

        self.setCentralWidget(central)

        for keys, slot in (
            (QKeySequence(Qt.Key_PageDown), lambda: self.go_to_page(self._page_index + 1)),
            (QKeySequence(Qt.Key_PageUp), lambda: self.go_to_page(self._page_index - 1)),
            (QKeySequence(Qt.Key_Right), lambda: self.go_to_page(self._page_index + 1)),
            (QKeySequence(Qt.Key_Left), lambda: self.go_to_page(self._page_index - 1)),
            (QKeySequence("Ctrl+="), lambda: self.view.zoom(1.25)),
            (QKeySequence("Ctrl+-"), lambda: self.view.zoom(0.8)),
        ):
            QShortcut(keys, self, activated=slot)

    def _menu_action(self, menu, text, slot, shortcut=None):
        action = menu.addAction(text)
        action.triggered.connect(slot)
        if shortcut is not None:
            action.setShortcut(shortcut)
        return action

    def _build_menu(self) -> None:
        m = self.menuBar()
        file_menu = m.addMenu("&File")
        self._menu_action(file_menu, "&Open…", self._choose_file, QKeySequence.Open)
        self.save_action = self._menu_action(
            file_menu, "&Save searchable copy…", self._choose_export_path, QKeySequence.Save
        )
        self.save_action.setEnabled(False)
        file_menu.addSeparator()
        self._menu_action(file_menu, "E&xit", self.close)

        tools = m.addMenu("&Tools")
        self._menu_action(tools, "&Clear OCR cache", self._clear_cache)
        self._menu_action(tools, "&Re-OCR this document", self._reocr)

        self._menu_action(m.addMenu("&Help"), "&About", self._about)

    # ---------- open / render ----------

    def _choose_file(self) -> None:
        start = self.config.last_dir or os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(self, "Open PDF", start, "PDF files (*.pdf)")
        if path:
            self.open_pdf(path)

    def open_pdf(self, path: str, *, background_ocr: bool = True) -> None:
        if self._worker is not None:
            self._worker.stop()
        if self._doc is not None:
            self._doc.close()

        try:
            self._doc = Document.open(path)
        except DocumentError as exc:
            QMessageBox.critical(self, "Cannot open", str(exc))
            return

        self.config.last_dir = os.path.dirname(path)
        self._spans = {}
        self._active_query = ""
        self.results.clear()
        self.results.hide()
        self.setWindowTitle(f"PDF OCR Reader — {os.path.basename(path)}")

        # native-text and already-cached pages are available at once; the
        # worker fills in the image-only pages in the background.
        for i in range(self._doc.page_count):
            self._spans[i] = self._doc.page_spans(i, ocr=False)

        self.page_spin.setMaximum(self._doc.page_count)
        self.page_total.setText(f"of {self._doc.page_count}")
        self._populate_thumbnails()
        self.go_to_page(0)
        self.save_action.setEnabled(True)
        if background_ocr:
            self._start_worker(path)

    def _populate_thumbnails(self) -> None:
        self.thumbs.clear()
        for i in range(self._doc.page_count):
            png = render_page(self._doc._doc[i], dpi=_THUMB_DPI).png_bytes
            image = QImage.fromData(QByteArray(png), "PNG")
            item = QListWidgetItem(QIcon(QPixmap.fromImage(image)), f"{i + 1}")
            self.thumbs.addItem(item)

    def go_to_page(self, index: int) -> None:
        if self._doc is None:
            return
        index = max(0, min(index, self._doc.page_count - 1))
        self._page_index = index
        png = render_page(self._doc._doc[index], dpi=self.config.render_dpi).png_bytes
        self.view.show_page(png)
        self._apply_highlights_for_active_search()

        for widget, value in ((self.page_spin, index + 1), (self.thumbs, index)):
            widget.blockSignals(True)
            (widget.setValue if widget is self.page_spin else widget.setCurrentRow)(value)
            widget.blockSignals(False)

    def _source_dpi(self, page_index: int) -> int:
        return 72 if self._doc.has_text_layer(page_index) else self.config.ocr_dpi

    # ---------- OCR worker ----------

    def _start_worker(self, path: str) -> None:
        worker = OcrWorker(path)
        worker.pageSpans.connect(self._on_page_spans)
        worker.progress.connect(self._on_progress)
        worker.finished.connect(self._on_finished)
        worker.failed.connect(lambda m: self.status.setText(m))
        self._worker = worker
        self._thread = run_in_thread(worker)

    def _on_page_spans(self, page_index: int, spans) -> None:
        self._spans[page_index] = spans
        if self._active_query:
            self.run_search(self._active_query, refocus=False)

    def _on_progress(self, done: int, total: int) -> None:
        self.progress.setMaximum(total)
        self.progress.setValue(done)
        self.progress.show()
        self.status.setText(f"OCR {done}/{total}")

    def _on_finished(self) -> None:
        self.progress.hide()
        self.status.setText("")

    # ---------- search ----------

    def run_search(self, query: str, *, refocus: bool = True) -> None:
        self._active_query = query.strip()
        self.results.clear()
        if not self._active_query:
            self.results.hide()
            self.view.set_highlights([])
            return

        hits = search_spans(self._spans, self._active_query)
        for hit in hits:
            item = QListWidgetItem(f"p.{hit.page_index + 1}   {hit.snippet}")
            item.setData(Qt.UserRole, hit)
            self.results.addItem(item)
        self.results.show()
        self._apply_highlights_for_active_search()
        if refocus:
            self.search_box.setFocus()

    def _open_result(self, item: QListWidgetItem) -> None:
        hit = item.data(Qt.UserRole)
        if hit is None:
            return
        self.go_to_page(hit.page_index)

    def _apply_highlights_for_active_search(self) -> None:
        if self._doc is None or not self._active_query:
            self.view.set_highlights([])
            return
        spans = self._spans.get(self._page_index, [])
        terms = self._active_query.lower().split()
        source_dpi = self._source_dpi(self._page_index)
        rects = [
            scene_rect_for_span(
                s.bbox, source_dpi=source_dpi, render_dpi=self.config.render_dpi
            )
            for s in spans
            if any(t in s.text.lower() for t in terms)
        ]
        self.view.set_highlights(rects)

    # ---------- menu actions ----------

    def _choose_export_path(self) -> None:
        if self._doc is None:
            return
        stem = os.path.splitext(os.path.basename(self._doc.path))[0]
        default = os.path.join(self.config.last_dir or "", f"{stem} (searchable).pdf")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save searchable copy", default, "PDF files (*.pdf)"
        )
        if path:
            self.export_searchable(path)

    def export_searchable(self, path: str) -> None:
        if self._doc is None:
            return
        try:
            self._doc.ocr_all()  # ensure every image-only page has text
            save_searchable_pdf(self._doc, path)
        except (ExportError, OSError) as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return
        QMessageBox.information(self, "Saved", f"Searchable copy written to:\n{path}")

    def _clear_cache(self) -> None:
        count = cache.clear()
        QMessageBox.information(self, "OCR cache", f"Cleared {count} cached document(s).")

    def _reocr(self) -> None:
        if self._doc is None:
            return
        path = self._doc.path
        cache.write(self._doc.content_hash, {})  # overwrite with empty -> re-OCR on next open
        self.open_pdf(path)

    def _about(self) -> None:
        QMessageBox.about(
            self,
            "About PDF OCR Reader",
            "PDF OCR Reader 0.1.0\n\nOpen any scanned PDF, OCR it, and search inside it.\n"
            "OCR runs locally (RapidOCR, CPU). Your files never leave this computer.",
        )

    # ---------- lifecycle ----------

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        if self._worker is not None:
            self._worker.stop()
        if self._doc is not None:
            self._doc.close()
        save_config(self.config)
        super().closeEvent(event)
