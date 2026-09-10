from pdf_ocr_reader import cache


def test_write_then_read_round_trips(tmp_path):
    cache.write("abc123", {"page_count": 3, "pages": {"0": []}}, base=tmp_path)
    assert cache.read("abc123", base=tmp_path) == {"page_count": 3, "pages": {"0": []}}


def test_read_missing_returns_none(tmp_path):
    assert cache.read("nope", base=tmp_path) is None


def test_clear_removes_entries_and_counts_them(tmp_path):
    cache.write("a", {"x": 1}, base=tmp_path)
    cache.write("b", {"x": 2}, base=tmp_path)
    assert cache.clear(base=tmp_path) == 2
    assert cache.read("a", base=tmp_path) is None


def test_disk_usage_reports_bytes(tmp_path):
    cache.write("a", {"x": 1}, base=tmp_path)
    assert cache.disk_usage(base=tmp_path) > 0
