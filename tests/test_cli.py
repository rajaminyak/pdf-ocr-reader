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


def test_ocr_command_reports_completion(capsys, scanned_pdf):
    assert main(["ocr", scanned_pdf]) == 0
    assert "OCR complete: 1 page" in capsys.readouterr().out


def test_search_ocrs_then_finds_text_on_a_scanned_page(capsys, scanned_pdf):
    assert main(["search", scanned_pdf, "turbine"]) == 0
    out = capsys.readouterr().out
    assert "1 result(s)" in out
    assert "p.1" in out


def test_search_no_ocr_flag_skips_ocr(capsys, scanned_pdf):
    assert main(["search", scanned_pdf, "turbine", "--no-ocr"]) == 0
    assert "0 result(s)" in capsys.readouterr().out


def test_export_command_writes_a_searchable_pdf(capsys, scanned_pdf, tmp_path):
    out = tmp_path / "out.pdf"
    assert main(["export", scanned_pdf, str(out)]) == 0
    assert out.is_file()
    assert "Saved searchable copy" in capsys.readouterr().out

    import fitz

    d = fitz.open(str(out))
    got = d[0].get_text().lower()
    d.close()
    assert "turbine" in got or "bearing" in got


def test_export_over_source_exits_one(capsys, scanned_pdf):
    assert main(["export", scanned_pdf, scanned_pdf]) == 1
    assert "source" in capsys.readouterr().out.lower()
