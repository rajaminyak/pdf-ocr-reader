from __future__ import annotations

from PySide6.QtWidgets import QMainWindow

from pdf_ocr_reader.gui.config import load_config, save_config


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PDF OCR Reader")
        self.resize(1200, 850)
        self.config = load_config()

    def open_pdf(self, path: str) -> None:  # filled in Task 4
        pass

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        save_config(self.config)
        super().closeEvent(event)
