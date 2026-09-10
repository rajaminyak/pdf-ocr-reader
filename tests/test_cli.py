from pdf_ocr_reader.cli import main


def test_info_lists_pages_and_text_layer(capsys, born_digital_pdf):
    assert main(["info", born_digital_pdf]) == 0
    out = capsys.readouterr().out
    assert "pages: 2" in out
    assert "p.1: text layer" in out


def test_search_prints_hits(capsys, born_digital_pdf):
    assert main(["search", born_digital_pdf, "reactor"]) == 0
    out = capsys.readouterr().out
    assert "2 result(s)" in out
    assert "p.1" in out


def test_search_no_results_is_exit_zero(capsys, born_digital_pdf):
    assert main(["search", born_digital_pdf, "zzznotthere"]) == 0
    assert "0 result(s)" in capsys.readouterr().out


def test_missing_file_exits_one(capsys, tmp_path):
    assert main(["info", str(tmp_path / "nope.pdf")]) == 1
    assert "not found" in capsys.readouterr().out.lower()
