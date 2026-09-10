from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _base(base: Path | None) -> Path:
    if base is not None:
        return Path(base)
    root = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(root) / "PdfOcrReader"


def cache_root(base: Path | None = None) -> Path:
    path = _base(base) / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def read(file_hash: str, *, base: Path | None = None) -> dict | None:
    entry = cache_root(base) / f"{file_hash}.json"
    if not entry.is_file():
        return None
    try:
        return json.loads(entry.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def write(file_hash: str, payload: dict, *, base: Path | None = None) -> None:
    try:
        entry = cache_root(base) / f"{file_hash}.json"
        entry.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"pdf-ocr-reader: could not write cache ({exc})", file=sys.stderr)


def clear(*, base: Path | None = None) -> int:
    count = 0
    for entry in cache_root(base).glob("*.json"):
        try:
            entry.unlink()
            count += 1
        except OSError:
            pass
    return count


def disk_usage(*, base: Path | None = None) -> int:
    return sum(f.stat().st_size for f in cache_root(base).glob("*.json"))
