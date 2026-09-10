from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

from pdf_ocr_reader import ocr


def config_path() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "PdfOcrReader" / "config.toml"


@dataclass
class Config:
    last_dir: str = ""
    ocr_dpi: int = ocr.OCR_DPI
    render_dpi: int = 150


def load_config(path: Path | None = None) -> Config:
    path = path or config_path()
    if not path.exists():
        return Config()
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return Config(
        last_dir=str(data.get("last_dir", "")),
        ocr_dpi=int(data.get("ocr_dpi", ocr.OCR_DPI)),
        render_dpi=int(data.get("render_dpi", 150)),
    )


def save_config(cfg: Config, path: Path | None = None) -> None:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for key, value in asdict(cfg).items():
        if isinstance(value, str):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{key} = "{escaped}"')
        else:
            lines.append(f"{key} = {value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
