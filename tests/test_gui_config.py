from pdf_ocr_reader.gui.config import Config, load_config, save_config


def test_round_trips(tmp_path):
    p = tmp_path / "config.toml"
    cfg = Config(last_dir=r"C:\Users\me\Documents", ocr_dpi=300, render_dpi=200)
    save_config(cfg, p)
    assert load_config(p) == cfg


def test_missing_file_is_defaults(tmp_path):
    cfg = load_config(tmp_path / "nope.toml")
    assert cfg.last_dir == "" and cfg.ocr_dpi == 300
