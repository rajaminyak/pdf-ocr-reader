import subprocess
import sys


def test_core_imports_without_pyside6():
    code = (
        "import sys; sys.modules['PySide6'] = None;"
        "import pdf_ocr_reader.document, pdf_ocr_reader.renderer, pdf_ocr_reader.search,"
        " pdf_ocr_reader.textlayer, pdf_ocr_reader.cache, pdf_ocr_reader.models,"
        " pdf_ocr_reader.ocr, pdf_ocr_reader.cli;"
        "print('ok')"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "ok" in out.stdout
