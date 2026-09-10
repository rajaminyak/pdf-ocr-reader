from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from pdf_ocr_reader.gui.mainwindow import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    if len(sys.argv) > 1:
        window.open_pdf(sys.argv[1])
    return app.exec()
