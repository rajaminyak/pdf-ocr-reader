import pytest
from PySide6.QtCore import QCoreApplication

from pdf_ocr_reader.gui.worker import OcrWorker


@pytest.fixture(scope="module")
def qapp():
    return QCoreApplication.instance() or QCoreApplication([])


def test_worker_emits_spans_for_every_page_and_finishes(qapp, scanned_pdf):
    w = OcrWorker(scanned_pdf)
    seen = {"spans": {}, "progress": [], "finished": 0, "failed": None}
    w.pageSpans.connect(lambda i, s: seen["spans"].__setitem__(i, s))
    w.progress.connect(lambda d, t: seen["progress"].append((d, t)))
    w.finished.connect(lambda: seen.__setitem__("finished", seen["finished"] + 1))
    w.failed.connect(lambda m: seen.__setitem__("failed", m))

    w.run()

    assert seen["failed"] is None
    assert seen["finished"] == 1
    assert 0 in seen["spans"]
    joined = " ".join(s.text for s in seen["spans"][0]).lower()
    assert "turbine" in joined or "bearing" in joined
    assert seen["progress"][-1] == (1, 1)


def test_worker_reports_failure_for_a_bad_file(qapp, tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"nope")
    w = OcrWorker(str(bad))
    fails = []
    w.failed.connect(fails.append)
    w.run()
    assert fails and fails[0]
