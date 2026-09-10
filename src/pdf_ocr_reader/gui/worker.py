from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal

from pdf_ocr_reader.document import Document


class OcrWorker(QObject):
    pageSpans = Signal(int, object)  # (page_index, list[Span])
    progress = Signal(int, int)  # (done, total)
    finished = Signal()
    failed = Signal(str)

    def __init__(self, path: str) -> None:
        super().__init__()
        self._path = path
        self._stopped = False

    def stop(self) -> None:
        self._stopped = True

    def run(self) -> None:
        try:
            doc = Document.open(self._path)
            for i in range(doc.page_count):
                self.pageSpans.emit(i, doc.page_spans(i, ocr=False))

            pending = doc._pages_needing_ocr()
            total = len(pending)
            for done, page_index in enumerate(pending, start=1):
                if self._stopped:
                    break
                doc._ocr_pages[page_index] = doc._ocr_page(page_index)
                doc._persist_cache()
                self.pageSpans.emit(page_index, doc._ocr_pages[page_index])
                self.progress.emit(done, total)

            doc.close()
            self.finished.emit()
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI
            self.failed.emit(f"{type(exc).__name__}: {exc}")


def run_in_thread(worker: QObject) -> QThread:
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    worker.failed.connect(thread.quit)
    thread.start()
    return thread
