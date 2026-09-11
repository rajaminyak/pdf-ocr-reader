"""PyInstaller entry point — thin wrapper so PyInstaller has a script to analyze."""
import sys

from pdf_ocr_reader.gui.app import main

if __name__ == "__main__":
    sys.exit(main())
