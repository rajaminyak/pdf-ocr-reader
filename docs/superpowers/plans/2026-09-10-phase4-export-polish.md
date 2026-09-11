# Phase 4: Searchable-PDF Export + Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** "Save searchable copy…" — write a new PDF that carries an invisible OCR text layer, so it is Ctrl+F-searchable in Acrobat / Edge / any reader. Wire it into the CLI and the GUI (enable the menu item that Phase 3 left disabled). Plus two small polish fixes.

**Architecture:** New `exporter` module (core, GUI-free): opens the source with PyMuPDF, and for every page that was OCR'd (image-only pages), draws each OCR span's text invisibly (`render_mode=3`) at the span's position converted from OCR-pixel space to PDF points. Native-text pages are already searchable and are copied unchanged. The source file is never modified — output goes to a new path. The GUI and CLI run `Document.ocr_all` first so every page has text, then call `exporter.save_searchable_pdf`.

**Tech Stack:** unchanged (PyMuPDF does the text injection).

**Spec:** `docs/superpowers/specs/2026-09-10-pdf-ocr-reader-design.md`

## Global Constraints

- `exporter` is core — no PySide6 import (add it to `test_core_has_no_gui_dep`).
- Never write to the source path. `save_searchable_pdf` refuses if `out_path` resolves to the same file as the source.
- Invisible text only (`render_mode=3`) — the visible page must look identical to the source.
- Coordinate conversion: an OCR span bbox is in pixels at `document.ocr_dpi`; a PDF point is `pixel * 72 / ocr_dpi`. Text is inserted at the top-left of the converted rect with `fontsize = rect_height_in_points` (clamped to a sane 4–24 pt range so a bad box can't produce a monster glyph).
- Export requires OCR to be complete for the document; callers run `ocr_all` first. `save_searchable_pdf` itself does not OCR — it only reads `document.page_spans(i, ocr=False)` (native or already-cached) and injects.

---

### Task 1: `exporter.save_searchable_pdf`

**Files:**
- Create: `src/pdf_ocr_reader/exporter.py`
- Test: `tests/test_exporter.py`

**Interfaces:**
- `exporter.ExportError(Exception)`
- `exporter.save_searchable_pdf(doc: Document, out_path: str) -> None` — writes `out_path`. Raises `ExportError` if `out_path` is the source file.

- [ ] **Step 1: Failing tests**

```python
import fitz
import pytest

from pdf_ocr_reader.document import Document
from pdf_ocr_reader.exporter import ExportError, save_searchable_pdf


def test_export_adds_a_searchable_layer_to_a_scanned_pdf(scanned_pdf, tmp_path):
    out = tmp_path / "scan (searchable).pdf"
    with Document.open(scanned_pdf) as doc:
        doc.ocr_all()
        save_searchable_pdf(doc, str(out))

    result = fitz.open(str(out))
    text = result[0].get_text().lower()
    result.close()
    assert "turbine" in text or "bearing" in text

    # source untouched: still image-only
    src = fitz.open(scanned_pdf)
    assert len(src[0].get_text().strip()) < 12
    src.close()


def test_export_keeps_a_born_digital_pdf_readable(born_digital_pdf, tmp_path):
    out = tmp_path / "born (searchable).pdf"
    with Document.open(born_digital_pdf) as doc:
        doc.ocr_all()  # nothing to do
        save_searchable_pdf(doc, str(out))
    result = fitz.open(str(out))
    assert "reactor" in result[0].get_text().lower()
    result.close()


def test_export_refuses_to_overwrite_the_source(scanned_pdf):
    with Document.open(scanned_pdf) as doc:
        with pytest.raises(ExportError):
            save_searchable_pdf(doc, scanned_pdf)
```

- [ ] **Step 2: Run — FAIL.**

- [ ] **Step 3: Implement `exporter.py`**

```python
from __future__ import annotations

import os

import fitz

from pdf_ocr_reader.document import Document

_MIN_FONT_PT = 4.0
_MAX_FONT_PT = 24.0


class ExportError(Exception):
    pass


def save_searchable_pdf(doc: Document, out_path: str) -> None:
    if os.path.abspath(out_path) == os.path.abspath(doc.path):
        raise ExportError("refusing to overwrite the source PDF")

    out = fitz.open(doc.path)
    try:
        for page_index in range(doc.page_count):
            if doc.has_text_layer(page_index):
                continue  # already searchable
            spans = doc.page_spans(page_index, ocr=False)
            if not spans:
                continue
            page = out[page_index]
            scale = 72.0 / doc.ocr_dpi
            for span in spans:
                x0, y0, x1, y1 = (v * scale for v in span.bbox)
                font_pt = max(_MIN_FONT_PT, min(_MAX_FONT_PT, y1 - y0))
                page.insert_text(
                    (x0, y1),  # baseline near the box bottom
                    span.text,
                    fontsize=font_pt,
                    render_mode=3,  # invisible
                    overlay=True,
                )
        out.save(out_path, garbage=3, deflate=True)
    finally:
        out.close()
```

- [ ] **Step 4: Run — PASS. Update `tests/test_core_has_no_gui_dep.py`** — add `pdf_ocr_reader.exporter` to the import list; run it.

- [ ] **Step 5: Full suite. Commit.**

```bash
git add src/pdf_ocr_reader/exporter.py tests/test_exporter.py tests/test_core_has_no_gui_dep.py
git commit -m "feat: exporter.save_searchable_pdf — invisible OCR text layer, source untouched"
```

---

### Task 2: CLI `export` command

**Files:**
- Modify: `src/pdf_ocr_reader/cli.py`
- Test: `tests/test_cli.py`

**Interface:** `pdf-ocr-reader export <in.pdf> <out.pdf>` — OCRs every image-only page (progress to stderr), then writes `<out.pdf>`. Prints `Saved searchable copy: <out.pdf>`. `ExportError` / an existing `out.pdf` that equals the source → message + exit 1.

- [ ] **Step 1: Failing tests** (append to `tests/test_cli.py`)

```python
def test_export_command_writes_a_searchable_pdf(capsys, scanned_pdf, tmp_path):
    out = tmp_path / "out.pdf"
    assert main(["export", scanned_pdf, str(out)]) == 0
    assert out.is_file()
    assert "Saved searchable copy" in capsys.readouterr().out

    import fitz

    d = fitz.open(str(out))
    assert "turbine" in d[0].get_text().lower() or "bearing" in d[0].get_text().lower()
    d.close()


def test_export_over_source_exits_one(capsys, scanned_pdf):
    assert main(["export", scanned_pdf, scanned_pdf]) == 1
    assert "source" in capsys.readouterr().out.lower()
```

- [ ] **Step 2: Run — FAIL.**

- [ ] **Step 3: Implement** — add the subparser and branch:

```python
    export_p = sub.add_parser("export", help="Write a Ctrl+F-searchable copy of the PDF")
    export_p.add_argument("pdf")
    export_p.add_argument("out")
```

```python
        if args.command == "export":
            from pdf_ocr_reader.exporter import ExportError, save_searchable_pdf

            doc.ocr_all(progress=lambda d, t: print(f"OCR {d}/{t}", file=sys.stderr))
            try:
                save_searchable_pdf(doc, args.out)
            except ExportError as exc:
                print(str(exc))
                return 1
            print(f"Saved searchable copy: {args.out}")
            return 0
```

- [ ] **Step 4: Run — PASS. Full suite. Commit.**

```bash
git add src/pdf_ocr_reader/cli.py tests/test_cli.py
git commit -m "feat: cli 'export' — OCR then write a searchable-PDF copy"
```

---

### Task 3: GUI — enable "Save searchable copy…"

**Files:**
- Modify: `src/pdf_ocr_reader/gui/mainwindow.py`
- Test: `tests/test_gui_mainwindow.py`

**Behaviour:**
- The `Save searchable copy…` action is enabled whenever a document is open.
- On trigger: `QFileDialog.getSaveFileName` with a default name `<source stem> (searchable).pdf` in `config.last_dir`. If the user picks a path:
  - If OCR is still running (`self._worker` active and progress visible), first run a blocking `self._doc.ocr_all()` on the main thread with a modal `QProgressDialog` (the doc's cache is shared with the worker, so pages the worker already did are skipped) — simplest correct approach for a first cut.
  - Call `exporter.save_searchable_pdf(self._doc, path)`.
  - `QMessageBox.information` "Saved: <path>" on success; `QMessageBox.critical` on `ExportError` / `OSError`.
- Add `MainWindow.export_searchable(path: str)` as the testable entry point (the menu handler just resolves the path then calls it).

- [ ] **Step 1: Failing test** (append)

```python
def test_export_searchable_writes_a_file(qapp, scanned_pdf, tmp_path):
    w = MainWindow()
    w.open_pdf(scanned_pdf)
    out = tmp_path / "copy.pdf"
    w.export_searchable(str(out))
    assert out.is_file()

    import fitz

    d = fitz.open(str(out))
    assert "turbine" in d[0].get_text().lower() or "bearing" in d[0].get_text().lower()
    d.close()
    w.close()


def test_save_action_enabled_after_open(qapp, born_digital_pdf):
    w = MainWindow()
    assert not w.save_action.isEnabled()
    w.open_pdf(born_digital_pdf)
    assert w.save_action.isEnabled()
    w.close()
```

- [ ] **Step 2: Implement.** `export_searchable(path)` runs `self._doc.ocr_all()` then `save_searchable_pdf`. Enable `self.save_action` at the end of `open_pdf`. Wire the menu action to a `_choose_export_path` handler.

- [ ] **Step 3: Run — PASS. Full suite.**

- [ ] **Step 4: Manual smoke** — open a scanned PDF, File → Save searchable copy…, pick a path, open the result in Edge, Ctrl+F a word from a scanned page.

- [ ] **Step 5: Commit**

```bash
git add src/pdf_ocr_reader/gui/mainwindow.py tests/test_gui_mainwindow.py
git commit -m "feat: GUI 'Save searchable copy…' — enabled on open, OCR-then-export"
```

---

### Task 4: Polish — snippet word boundary

**Files:**
- Modify: `src/pdf_ocr_reader/search.py`
- Test: `tests/test_search.py`

**Behaviour:** `_snippet` currently starts `width // 3` chars before the match, which usually lands mid-word (`...isual inspection`). Trim the leading fragment to the next space so it starts on a whole word (`...visual inspection` or `... inspection`). Same for the trailing end — trim back to the last space. Keep the leading/trailing `...` markers.

- [ ] **Step 1: Failing test** (append to `tests/test_search.py`)

```python
def test_snippet_starts_and_ends_on_word_boundaries():
    from pdf_ocr_reader.search import _snippet

    text = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    s = _snippet(text, "epsilon", 24)
    assert s.startswith("...") and s.endswith("...")
    core = s.strip(".").strip()
    assert not core.split()[0].startswith("elta")  # no mid-word head
    assert core.split()[0] in {"delta", "gamma", "epsilon"}
```

- [ ] **Step 2: Implement** — after computing `piece = text[start:end]`, if `start > 0` drop everything up to and including the first space; if `end < len(text)` drop everything from the last space. Guard against a `piece` with no spaces (leave as-is).

- [ ] **Step 3: Run — PASS. Full suite. Commit.**

```bash
git add src/pdf_ocr_reader/search.py tests/test_search.py
git commit -m "polish: search snippets start and end on word boundaries"
```

---

### Task 5: Real-PDF validation

**Files:** none. Append findings.

- [ ] `py -3 -m pdf_ocr_reader.cli export "C:\Users\Ridho\Documents\Inspection Report - 31-E-101.pdf" "%TEMP%\inspection-searchable.pdf"`
- [ ] Open the output in Microsoft Edge (or Acrobat). Ctrl+F a word that is only on a scanned page ("hydrojet", "reboiler"). Confirm it is found and the highlight sits on the right text. Confirm the page looks visually identical to the original.
- [ ] Record: file, OCR time, output size vs input, whether Edge's find works, whether the invisible text is truly invisible (no faint ghosting). Commit the note. Delete the scratch output.

```bash
git add docs/superpowers/plans/2026-09-10-phase4-export-polish.md
git commit -m "docs: record Phase 4 export validation"
```

---

## Phase 4 validation results

Real-PDF: `C:\Users\Ridho\Documents\Inspection Report - 31-E-101.pdf` via
`pdf-ocr-reader export`.

| | |
|---|---|
| Size | 62 KB → 80 KB (+18 KB for the text layer) |
| Page 1 searchable chars | 2074 (was an unusable broken-font layer) |
| `search_for("hydrojet")` in output | found — a word that was **only on the scanned page** |
| `search_for("reboiler")` | found, sensible page rect |
| Source | unchanged |

**Note:** page 1 carried a broken-encoding "text layer" (Phase 1's
`_is_readable` correctly treats it as image-only, so the exporter OCRs it).
The source's junk text is still copied into the output underneath the new
invisible OCR layer — harmless (invisible, and `search_for` matches the OCR
text) but not pristine. Stripping a source text layer risks losing good
content on mixed docs, so it is left in.

Word-boundary snippets confirmed (`_snippet` unit test): `...delta epsilon
zeta...` instead of `...elta epsilon zet...`.

## Self-Review

**Spec coverage:** "Save searchable copy" — invisible text layer, source
never modified, works from CLI and GUI. Snippet polish. Save-action enabled.
Installer is Phase 5.

**Placeholder scan:** none.

**Type consistency:** `exporter.save_searchable_pdf(doc: Document, out_path)`
matches the CLI and GUI call sites. `doc.ocr_dpi` (Phase 2) is the scale
denominator. `doc.has_text_layer` / `doc.page_spans(i, ocr=False)` (Phase 1/2)
reused unchanged. `_snippet` signature unchanged.

**Ambiguity:** font size is clamped 4–24 pt. Native pages are skipped in the
export loop (already searchable) — stated. Export requires OCR done;
callers run `ocr_all` first, `save_searchable_pdf` never OCRs (stated in
Global Constraints).
