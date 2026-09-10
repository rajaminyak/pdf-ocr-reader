import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import fitz
import pytest


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    # onnxruntime (RapidOCR) + Qt leave non-joinable threads that can hang the
    # interpreter shutdown on Windows. The terminal summary has already been
    # written by the time this trylast hook runs; skip the hanging teardown.
    import sys

    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(int(exitstatus))


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path_factory, monkeypatch):
    """Every test writes its OCR cache under a throwaway dir, never the real
    %LOCALAPPDATA%\\PdfOcrReader."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path_factory.mktemp("localappdata")))


@pytest.fixture
def born_digital_pdf(tmp_path):
    """A 2-page PDF with a real text layer."""
    path = tmp_path / "born.pdf"
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((72, 72), "Inspection report for the 37-R-101B reactor")
    p1.insert_text((72, 96), "differential pressure trending stable")
    p2 = doc.new_page()
    p2.insert_text((72, 72), "Recommendation continue monitoring the reactor weekly")
    doc.save(str(path))
    doc.close()
    return str(path)


@pytest.fixture
def scanned_pdf(tmp_path):
    """A 1-page PDF that is an image of text with NO text layer."""
    path = tmp_path / "scan.pdf"
    src = fitz.open()
    sp = src.new_page()
    sp.insert_text((72, 72), "SCANNED PAGE turbine bearing temperature high")
    pix = sp.get_pixmap(dpi=150)
    src.close()

    out = fitz.open()
    page = out.new_page(width=pix.width * 72 / 150, height=pix.height * 72 / 150)
    page.insert_image(page.rect, pixmap=pix)
    out.save(str(path))
    out.close()
    return str(path)
