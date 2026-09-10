# Phase 1: Core — Open, Render, Native Text, Search — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** A GUI-free core that opens any PDF, renders a page to an image, reads an existing text layer, and searches inside the document — plus a small CLI to prove it. No OCR yet (Phase 2).

**Architecture:** One `src/pdf_ocr_reader/` package. `models` holds the shared dataclasses. `renderer` rasterizes a page (returns raw PNG bytes + dimensions — NOT a Qt object, so the core stays Qt-free). `textlayer` reads word boxes from a born-digital PDF. `document` ties a file to its per-page spans (native text in this phase; an OCR fallback slots in at Phase 2). `cache` is the on-disk OCR store, scaffolded now and exercised in Phase 2. `search` scans a `Document` for page hits with matched bounding boxes. `cli` wires it together for a smoke test.

**Tech Stack:** Python 3.11+, PyMuPDF (`pymupdf`, imported as `fitz`), stdlib (`hashlib`, `json`, `pathlib`, `argparse`), pytest.

**Spec:** `docs/superpowers/specs/2026-09-10-pdf-ocr-reader-design.md`

## Global Constraints

- The core never imports PySide6 / PyQt. A test enforces it (Task 8). The renderer returns `RenderedPage` (PNG bytes + width/height/dpi), never a `QImage` — the GUI converts.
- Never modify the source PDF. Phase 1 only opens read-only and reads.
- `Span.bbox` is `(x0, y0, x1, y1)` in the coordinate space it came from: for native text, PDF points (the page's own coordinate system, origin top-left as PyMuPDF reports it). Phase 2's OCR spans will be in render-pixel space and carry their own dpi — do not assume the two are the same space; Phase 1 only produces native spans.
- All timestamps in cache entries are UTC ISO-8601.
- A `Document` owns its `fitz.Document` handle and must be closeable / usable as a context manager.

---

### Task 1: Project skeleton + shared models

**Files:**
- Create: `pyproject.toml`
- Create: `src/pdf_ocr_reader/__init__.py` (empty)
- Create: `src/pdf_ocr_reader/models.py`
- Create: `tests/__init__.py` (empty)
- Test: `tests/test_models.py`

- [ ] **Step 1: `pyproject.toml`**

```toml
[project]
name = "pdf-ocr-reader"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pymupdf>=1.24",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
pdf-ocr-reader = "pdf_ocr_reader.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
```

- [ ] **Step 2: Write the failing test** (`tests/test_models.py`)

```python
from pdf_ocr_reader.models import PageHit, RenderedPage, Span


def test_span_is_frozen_with_text_and_bbox():
    s = Span(text="reactor", bbox=(10.0, 20.0, 90.0, 32.0))
    assert s.text == "reactor"
    assert s.bbox == (10.0, 20.0, 90.0, 32.0)


def test_rendered_page_carries_png_bytes_and_dimensions():
    r = RenderedPage(png_bytes=b"\x89PNG", width=1240, height=1754, dpi=150)
    assert r.png_bytes.startswith(b"\x89PNG")
    assert (r.width, r.height, r.dpi) == (1240, 1754, 150)


def test_page_hit_holds_index_snippet_and_span_bboxes():
    h = PageHit(page_index=3, snippet="…feed to the reactor…", span_bboxes=[(1.0, 2.0, 3.0, 4.0)])
    assert h.page_index == 3
    assert "reactor" in h.snippet
    assert h.span_bboxes == [(1.0, 2.0, 3.0, 4.0)]
```

- [ ] **Step 3: Run — FAIL** (`ModuleNotFoundError`). `py -3 -m pytest tests/test_models.py -q`

- [ ] **Step 4: Implement `models.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field

BBox = tuple[float, float, float, float]  # (x0, y0, x1, y1)


@dataclass(frozen=True)
class Span:
    text: str
    bbox: BBox


@dataclass(frozen=True)
class RenderedPage:
    png_bytes: bytes
    width: int
    height: int
    dpi: int


@dataclass(frozen=True)
class PageHit:
    page_index: int
    snippet: str
    span_bboxes: list[BBox] = field(default_factory=list)
```

- [ ] **Step 5: Run — PASS.** `py -3 -m pip install -e ".[dev]"` then `py -3 -m pytest -q`.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/pdf_ocr_reader/__init__.py src/pdf_ocr_reader/models.py tests/
git commit -m "feat: project skeleton and shared models (Span, RenderedPage, PageHit)"
```

---

### Task 2: `textlayer` — read native word boxes

**Files:**
- Create: `src/pdf_ocr_reader/textlayer.py`
- Test: `tests/conftest.py`, `tests/test_textlayer.py`

**Interfaces:**
- `textlayer.MIN_NATIVE_CHARS: int = 12`
- `textlayer.native_page_spans(page: fitz.Page) -> list[Span] | None` — returns one `Span` per word from `page.get_text("words")`, or `None` if the page has fewer than `MIN_NATIVE_CHARS` characters of extractable text (treat as image-only).

- [ ] **Step 1: Shared fixtures** (`tests/conftest.py`)

```python
import fitz
import pytest


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
```

- [ ] **Step 2: Failing tests** (`tests/test_textlayer.py`)

```python
import fitz

from pdf_ocr_reader.textlayer import native_page_spans


def test_native_spans_from_born_digital_page(born_digital_pdf):
    doc = fitz.open(born_digital_pdf)
    spans = native_page_spans(doc[0])
    doc.close()

    assert spans is not None
    words = [s.text for s in spans]
    assert "37-R-101B" in words
    assert "reactor" in words
    for s in spans:
        x0, y0, x1, y1 = s.bbox
        assert x1 > x0 and y1 > y0


def test_native_spans_none_for_image_only_page(scanned_pdf):
    doc = fitz.open(scanned_pdf)
    spans = native_page_spans(doc[0])
    doc.close()
    assert spans is None
```

- [ ] **Step 3: Run — FAIL.** `py -3 -m pytest tests/test_textlayer.py -q`

- [ ] **Step 4: Implement `textlayer.py`**

```python
from __future__ import annotations

import fitz

from pdf_ocr_reader.models import Span

MIN_NATIVE_CHARS = 12


def native_page_spans(page: fitz.Page) -> list[Span] | None:
    words = page.get_text("words")  # (x0, y0, x1, y1, "word", block, line, word_no)
    total_chars = sum(len(w[4]) for w in words)
    if total_chars < MIN_NATIVE_CHARS:
        return None
    return [
        Span(text=w[4], bbox=(float(w[0]), float(w[1]), float(w[2]), float(w[3])))
        for w in words
        if w[4].strip()
    ]
```

- [ ] **Step 5: Run — PASS. Commit.**

```bash
git add src/pdf_ocr_reader/textlayer.py tests/conftest.py tests/test_textlayer.py
git commit -m "feat: textlayer.native_page_spans — word boxes from a born-digital page"
```

---

### Task 3: `renderer` — page to PNG bytes

**Files:**
- Create: `src/pdf_ocr_reader/renderer.py`
- Test: `tests/test_renderer.py`

**Interfaces:**
- `renderer.render_page(page: fitz.Page, dpi: int = 150) -> RenderedPage` — rasterizes the page at `dpi`, returns PNG bytes plus pixel dimensions and the dpi used.

- [ ] **Step 1: Failing tests**

```python
import fitz

from pdf_ocr_reader.renderer import render_page


def test_render_returns_png_bytes_and_dimensions(born_digital_pdf):
    doc = fitz.open(born_digital_pdf)
    r = render_page(doc[0], dpi=150)
    doc.close()
    assert r.png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
    assert r.width > 0 and r.height > 0
    assert r.dpi == 150


def test_higher_dpi_yields_larger_image(born_digital_pdf):
    doc = fitz.open(born_digital_pdf)
    small = render_page(doc[0], dpi=72)
    large = render_page(doc[0], dpi=200)
    doc.close()
    assert large.width > small.width and large.height > small.height
```

- [ ] **Step 2: Run — FAIL.**

- [ ] **Step 3: Implement `renderer.py`**

```python
from __future__ import annotations

import fitz

from pdf_ocr_reader.models import RenderedPage


def render_page(page: fitz.Page, dpi: int = 150) -> RenderedPage:
    pix = page.get_pixmap(dpi=dpi)
    return RenderedPage(
        png_bytes=pix.tobytes("png"),
        width=pix.width,
        height=pix.height,
        dpi=dpi,
    )
```

- [ ] **Step 4: Run — PASS. Commit.**

```bash
git add src/pdf_ocr_reader/renderer.py tests/test_renderer.py
git commit -m "feat: renderer.render_page — page to PNG bytes at a given dpi"
```

---

### Task 4: `cache` — on-disk OCR store (scaffold)

**Files:**
- Create: `src/pdf_ocr_reader/cache.py`
- Test: `tests/test_cache.py`

**Interfaces:**
- `cache.cache_root(base: Path | None = None) -> Path` — `<base or %LOCALAPPDATA%>\PdfOcrReader\cache`, created on access. `base` param exists for tests.
- `cache.read(file_hash: str, *, base: Path | None = None) -> dict | None` — parsed JSON for that hash, or `None`.
- `cache.write(file_hash: str, payload: dict, *, base: Path | None = None) -> None` — writes `<hash>.json` (pretty). Never raises on an unwritable directory — logs to stderr and returns.
- `cache.clear(*, base: Path | None = None) -> int` — deletes every `*.json`, returns the count.
- `cache.disk_usage(*, base: Path | None = None) -> int` — total bytes of `*.json`.

- [ ] **Step 1: Failing tests**

```python
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
```

- [ ] **Step 2: Run — FAIL.**

- [ ] **Step 3: Implement `cache.py`**

```python
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
```

- [ ] **Step 4: Run — PASS. Commit.**

```bash
git add src/pdf_ocr_reader/cache.py tests/test_cache.py
git commit -m "feat: cache — per-file JSON OCR store (read/write/clear/usage)"
```

---

### Task 5: `document.Document`

**Files:**
- Create: `src/pdf_ocr_reader/document.py`
- Test: `tests/test_document.py`

**Interfaces:**
- `document.DocumentError(Exception)` — raised for a file that cannot be opened as a PDF.
- `document.Document` — construct via `Document.open(path: str) -> Document`. Attributes: `path: str`, `page_count: int`, `content_hash: str` (SHA-256 hex of the file bytes). Methods:
  - `page_spans(page_index: int) -> list[Span]` — native spans for the page, or `[]` when the page is image-only (Phase 2 overrides this branch with OCR).
  - `full_page_text(page_index: int) -> str` — the page's spans joined by single spaces.
  - `has_text_layer(page_index: int) -> bool`.
  - `close() -> None`; also works as a context manager (`__enter__`/`__exit__`).

- [ ] **Step 1: Failing tests**

```python
import pytest

from pdf_ocr_reader.document import Document, DocumentError


def test_open_reports_page_count_and_stable_hash(born_digital_pdf):
    with Document.open(born_digital_pdf) as doc:
        assert doc.page_count == 2
        h1 = doc.content_hash
    with Document.open(born_digital_pdf) as doc:
        assert doc.content_hash == h1
    assert len(h1) == 64


def test_page_spans_and_text_from_born_digital(born_digital_pdf):
    with Document.open(born_digital_pdf) as doc:
        assert doc.has_text_layer(0) is True
        assert "37-R-101B" in doc.full_page_text(0)
        assert any(s.text == "reactor" for s in doc.page_spans(0))


def test_image_only_page_has_no_text_layer_and_empty_spans(scanned_pdf):
    with Document.open(scanned_pdf) as doc:
        assert doc.has_text_layer(0) is False
        assert doc.page_spans(0) == []
        assert doc.full_page_text(0) == ""


def test_corrupt_file_raises_document_error(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf at all")
    with pytest.raises(DocumentError):
        Document.open(str(bad))
```

- [ ] **Step 2: Run — FAIL.**

- [ ] **Step 3: Implement `document.py`**

```python
from __future__ import annotations

import hashlib

import fitz

from pdf_ocr_reader import textlayer
from pdf_ocr_reader.models import Span


class DocumentError(Exception):
    pass


def _hash_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


class Document:
    def __init__(self, path: str, doc: fitz.Document) -> None:
        self.path = path
        self._doc = doc
        self.page_count = doc.page_count
        self.content_hash = _hash_file(path)

    @classmethod
    def open(cls, path: str) -> "Document":
        try:
            doc = fitz.open(path)
        except Exception as exc:  # noqa: BLE001 - normalize to one error type
            raise DocumentError(f"cannot open {path!r}: {exc}") from exc
        if not doc.is_pdf:
            doc.close()
            raise DocumentError(f"not a PDF: {path!r}")
        return cls(path, doc)

    def page_spans(self, page_index: int) -> list[Span]:
        spans = textlayer.native_page_spans(self._doc[page_index])
        return spans if spans is not None else []

    def full_page_text(self, page_index: int) -> str:
        return " ".join(s.text for s in self.page_spans(page_index))

    def has_text_layer(self, page_index: int) -> bool:
        return textlayer.native_page_spans(self._doc[page_index]) is not None

    def close(self) -> None:
        self._doc.close()

    def __enter__(self) -> "Document":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
```

- [ ] **Step 4: Run — PASS. Full suite. Commit.**

```bash
git add src/pdf_ocr_reader/document.py tests/test_document.py
git commit -m "feat: Document — open a PDF, page count, content hash, native page text"
```

---

### Task 6: `search`

**Files:**
- Create: `src/pdf_ocr_reader/search.py`
- Test: `tests/test_search.py`

**Interfaces:**
- `search.search(doc: Document, query: str, *, snippet_chars: int = 160) -> list[PageHit]` — for each page, lowercase the joined page text; a page matches when **every** whitespace-split term of `query` appears in it. Results are ranked by total term-occurrence count (descending), then by page index (ascending). Each `PageHit`:
  - `page_index`
  - `snippet` — up to `snippet_chars` of the original-case page text, windowed around the first occurrence of the first term (prefix/suffix `…` when truncated)
  - `span_bboxes` — the bbox of every span on that page whose (lowercased) text contains any query term.
- Blank query → `[]`.

- [ ] **Step 1: Failing tests**

```python
from pdf_ocr_reader.document import Document
from pdf_ocr_reader.search import search


def test_single_term_finds_the_right_pages(born_digital_pdf):
    with Document.open(born_digital_pdf) as doc:
        hits = search(doc, "reactor")
    pages = {h.page_index for h in hits}
    assert pages == {0, 1}
    assert all("reactor" in h.snippet.lower() for h in hits)


def test_ranks_page_with_more_occurrences_first(tmp_path):
    import fitz

    p = tmp_path / "rank.pdf"
    d = fitz.open()
    d.new_page().insert_text((72, 72), "pompa sekali saja disebut")
    d.new_page().insert_text((72, 72), "pompa pompa pompa tiga kali")
    d.save(str(p))
    d.close()

    with Document.open(str(p)) as doc:
        hits = search(doc, "pompa")
    assert [h.page_index for h in hits] == [1, 0]


def test_and_of_terms_requires_all_on_the_page(born_digital_pdf):
    with Document.open(born_digital_pdf) as doc:
        hits = search(doc, "reactor monitoring")
    assert [h.page_index for h in hits] == [1]


def test_hit_carries_matching_span_bboxes(born_digital_pdf):
    with Document.open(born_digital_pdf) as doc:
        hits = search(doc, "reactor")
    first = next(h for h in hits if h.page_index == 0)
    assert first.span_bboxes
    for x0, y0, x1, y1 in first.span_bboxes:
        assert x1 > x0 and y1 > y0


def test_blank_query_returns_nothing(born_digital_pdf):
    with Document.open(born_digital_pdf) as doc:
        assert search(doc, "   ") == []
```

- [ ] **Step 2: Run — FAIL.**

- [ ] **Step 3: Implement `search.py`**

```python
from __future__ import annotations

from pdf_ocr_reader.document import Document
from pdf_ocr_reader.models import PageHit


def _snippet(text: str, term: str, width: int) -> str:
    lowered = text.lower()
    pos = lowered.find(term)
    if pos == -1:
        return text[:width] + ("…" if len(text) > width else "")
    start = max(0, pos - width // 3)
    end = min(len(text), start + width)
    piece = text[start:end]
    return ("…" if start > 0 else "") + piece + ("…" if end < len(text) else "")


def search(doc: Document, query: str, *, snippet_chars: int = 160) -> list[PageHit]:
    terms = [t for t in query.lower().split() if t]
    if not terms:
        return []

    hits: list[tuple[int, int, PageHit]] = []  # (-score, page_index, hit)
    for page_index in range(doc.page_count):
        spans = doc.page_spans(page_index)
        text = " ".join(s.text for s in spans)
        lowered = text.lower()
        if not all(term in lowered for term in terms):
            continue
        score = sum(lowered.count(term) for term in terms)
        boxes = [s.bbox for s in spans if any(term in s.text.lower() for term in terms)]
        hit = PageHit(
            page_index=page_index,
            snippet=_snippet(text, terms[0], snippet_chars),
            span_bboxes=boxes,
        )
        hits.append((-score, page_index, hit))

    hits.sort(key=lambda t: (t[0], t[1]))
    return [h for _, _, h in hits]
```

- [ ] **Step 4: Run — PASS. Full suite. Commit.**

```bash
git add src/pdf_ocr_reader/search.py tests/test_search.py
git commit -m "feat: search — AND-of-terms page hits with snippet and matched bboxes"
```

---

### Task 7: `cli`

**Files:**
- Create: `src/pdf_ocr_reader/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- `cli.main(argv: list[str] | None = None) -> int`
- `pdf-ocr-reader info <pdf>` → prints `pages: N` then one line per page `p.<i+1>: text layer` / `p.<i+1>: image only`.
- `pdf-ocr-reader search <pdf> <query...>` → prints `<n> result(s)` then `p.<i+1>  <snippet>` per hit; exit 0 even with zero results. Missing file → message + exit 1. Not a PDF → message + exit 1.

- [ ] **Step 1: Failing tests**

```python
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
```

- [ ] **Step 2: Run — FAIL.**

- [ ] **Step 3: Implement `cli.py`**

```python
from __future__ import annotations

import argparse
import os
import sys

from pdf_ocr_reader.document import Document, DocumentError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pdf-ocr-reader")
    sub = parser.add_subparsers(dest="command", required=True)

    info_p = sub.add_parser("info", help="Page count and per-page text-layer status")
    info_p.add_argument("pdf")

    search_p = sub.add_parser("search", help="Search inside a PDF (native text only in Phase 1)")
    search_p.add_argument("pdf")
    search_p.add_argument("query", nargs="+")

    args = parser.parse_args(argv)

    if not os.path.isfile(args.pdf):
        print(f"File not found: {args.pdf}")
        return 1

    try:
        doc = Document.open(args.pdf)
    except DocumentError as exc:
        print(str(exc))
        return 1

    try:
        if args.command == "info":
            print(f"pages: {doc.page_count}")
            for i in range(doc.page_count):
                kind = "text layer" if doc.has_text_layer(i) else "image only"
                print(f"p.{i + 1}: {kind}")
            return 0

        from pdf_ocr_reader.search import search as run_search

        hits = run_search(doc, " ".join(args.query))
        print(f"{len(hits)} result(s)")
        for h in hits:
            print(f"p.{h.page_index + 1}  {h.snippet}")
        return 0
    finally:
        doc.close()
```

- [ ] **Step 4: Run — PASS. Full suite. Commit.**

```bash
git add src/pdf_ocr_reader/cli.py tests/test_cli.py
git commit -m "feat: cli — 'info' and 'search' subcommands"
```

---

### Task 8: Engine-isolation test + real-PDF smoke

**Files:**
- Create: `tests/test_core_has_no_gui_dep.py`

- [ ] **Step 1: Isolation test**

```python
import subprocess
import sys


def test_core_imports_without_pyside6():
    code = (
        "import sys; sys.modules['PySide6'] = None;"
        "import pdf_ocr_reader.document, pdf_ocr_reader.renderer, pdf_ocr_reader.search,"
        " pdf_ocr_reader.textlayer, pdf_ocr_reader.cache, pdf_ocr_reader.models,"
        " pdf_ocr_reader.cli;"
        "print('ok')"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "ok" in out.stdout
```

- [ ] **Step 2: Run — PASS. Full suite green.**

- [ ] **Step 3: Real-PDF smoke (manual, no test cycle)**

Pick one born-digital PDF and one scanned PDF from a real source (e.g. the
memo archive at `E:\4. DATA MEMO KELUAR PE` has both). Run:

```bash
py -3 -m pdf_ocr_reader.cli info "<born-digital>.pdf"
py -3 -m pdf_ocr_reader.cli search "<born-digital>.pdf" <a word you know is in it>
py -3 -m pdf_ocr_reader.cli info "<scanned>.pdf"
```

Confirm: born-digital `info` shows "text layer" for its pages and `search`
returns the right page(s); scanned `info` shows "image only" for every page
and `search` returns `0 result(s)` (OCR is Phase 2). Record the two file
names and the observed output in a short "Phase 1 validation" note appended
to this plan; commit it.

```bash
git add tests/test_core_has_no_gui_dep.py docs/superpowers/plans/2026-09-10-phase1-core-render-search.md
git commit -m "test: core imports without PySide6; record Phase 1 validation"
```

---

## Self-Review

**Spec coverage (Phase 1 slice):** `renderer`, `textlayer`, `document`
(native-only), `cache` (scaffold), `search` (page hits + bboxes + AND-of-terms
+ snippet), CLI smoke, core-is-GUI-free test — all present. OCR, GUI, export,
installer are later phases and explicitly out of this plan.

**Placeholder scan:** none — every step has literal code or a literal command.

**Type consistency:** `Span` (`text`, `bbox`) defined in Task 1, consumed by
`textlayer` (Task 2), `document` (Task 5), `search` (Task 6). `RenderedPage`
defined Task 1, produced Task 3. `PageHit` (`page_index`, `snippet`,
`span_bboxes`) defined Task 1, produced Task 6, printed Task 7. `Document`
public surface (`open`, `page_count`, `content_hash`, `page_spans`,
`full_page_text`, `has_text_layer`, `close`, context manager) defined Task 5
and used unchanged by `search` (Task 6) and `cli` (Task 7). `cache` functions
all take the same `base=` test hook.

**Ambiguity:** `native_page_spans` returning `None` vs `[]` is explicit
(`None` = image-only page, `[]` never returned by it; `Document.page_spans`
converts `None`→`[]`). Snippet windowing is pinned (`width // 3` before the
match, `…` only when truncated). Ranking key is explicit (`(-score, page)`).
