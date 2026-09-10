# PDF OCR Reader — Design

**Date:** 2026-09-10
**Status:** Approved for planning
**Owner:** Ridho (Process Engineering, RU VI Balongan)

## Problem

Engineers regularly get scanned engineering PDFs — vendor reports, marked-up
drawings, old inspection records, meeting minutes — with no text layer. To
find one number, tag, or clause you scroll through every page by eye. There
is no quick "open this scan and search inside it".

The existing Refinery Doc Organizer solves corpus-wide search over the PE
memo archive. This is different: an **ad-hoc, single-document reader** for
*any* scanned PDF, usable by anyone on the team without setting up a corpus
or an index.

## Goals

1. **Open any PDF and read it** — render pages, page thumbnails, zoom,
   next/previous, go-to-page.
2. **Search inside it** — type a query, get a list of hits (page + text
   snippet), click a hit to jump to that page with the match highlighted.
3. **Good OCR on scans** — recognize Indonesian and English text on typical
   office scans (300 dpi, some skew, stamps, tables).
4. **Fast enough to be usable** — the page you are looking at is readable
   immediately; OCR runs in the background; a document you have opened
   before opens instantly (cached).
5. **Portable** — one installer, no admin rights, no external programs to
   install, runs on any team Windows laptop (CPU only).

## Non-goals

- Not a corpus indexer or organizer (that is Refinery Doc Organizer).
- Not a PDF editor — never modifies the source file. "Save searchable copy"
  writes a *new* file.
- Not trying to beat cloud OCR accuracy — no document leaves the laptop.
- No form filling, annotation, redaction, or e-signature.
- No handwriting recognition beyond whatever the OCR engine gives for free.

## Architecture

```
┌───────────────────────────────────────────────┐
│  Desktop GUI (PySide6) — one window            │
│  - page view (rendered image + highlight box)  │
│  - thumbnail strip / page list                 │
│  - search bar + results list                   │
│  - OCR progress bar                            │
└───────────────┬───────────────────────────────┘
                │ calls
┌───────────────▼───────────────────────────────┐
│  Core (pure Python, no GUI import)             │
│  - renderer : PDF page -> QImage (PyMuPDF)     │
│  - textlayer: read an existing PDF text layer  │
│  - ocr      : image -> [(text, bbox)] (RapidOCR)│
│  - document : ties a PDF to its page text +    │
│               bboxes, native-or-OCR per page   │
│  - cache    : per-file OCR result store        │
│  - search   : query -> ranked page hits + spans │
│  - exporter : write a searchable-PDF copy      │
└───────────────┬───────────────┬────────────────┘
                │               │
      ┌─────────▼──────┐  ┌─────▼──────────┐
      │ OCR cache       │  │ RapidOCR ONNX  │
      │ %LOCALAPPDATA%\ │  │ models (pip-   │
      │ PdfOcrReader\   │  │ bundled, CPU)  │
      │ cache\<hash>.json│  │                │
      └─────────────────┘  └────────────────┘
```

The core never imports PySide6 (enforced by a test, as in Refinery Doc
Organizer). The GUI is a thin shell.

### Components

- **renderer** — `render_page(doc, page_index, dpi) -> QImage`. PyMuPDF
  (`fitz`) rasterizes the page. Scanned pages are already images; this just
  draws them. Cheap; the currently-viewed page always renders first.
- **textlayer** — `native_page_text(doc, page_index) -> list[Span] | None`.
  If the PDF already has a real text layer (`page.get_text("words")`
  returns meaningful content), use it verbatim with its word boxes and
  skip OCR for that page. Returns `None` when the page is image-only.
- **ocr** — `ocr_image(image_bytes) -> list[Span]` where
  `Span = {text, bbox=(x0,y0,x1,y1)}`. RapidOCR returns a 4-point polygon
  per line; `bbox` is its axis-aligned bounding rectangle. Coordinates are
  in the pixel space of the image that was OCR'd (i.e. the page rendered
  at `config.dpi`). The view stores that `ocr_dpi` alongside the spans and
  scales every bbox by `view_dpi / ocr_dpi` (and by the page's PDF
  MediaBox origin) when drawing highlights, so highlights stay aligned at
  any zoom. Wraps RapidOCR (ONNX Runtime, CPU), lifted from Refinery Doc
  Organizer's `ocr.py`.
- **document** — `Document.open(path)`; lazily produces per-page
  `list[Span]`: native text if present, else OCR (on demand or via a
  background sweep). Holds the page count, the source path, and the
  content hash.
- **cache** — keyed by SHA-256 of the file. Stores `{page_index:
  [Span,...], engine, dpi, created_at}` as JSON under
  `%LOCALAPPDATA%\PdfOcrReader\cache\<hash>.json`. A re-opened document
  with a matching hash loads its text instantly; no re-OCR. A "Clear
  cache" menu item and a size cap (evict oldest beyond ~500 MB).
- **search** — `search(document, query) -> list[PageHit]` where
  `PageHit = {page_index, snippet, spans=[bbox,...]}`. Case-insensitive
  substring across whole-page text (join spans with spaces); ranks by hit
  count then page order. Multi-word query = AND of terms on the page.
  Returns the span bboxes that matched so the view can highlight them.
- **exporter** — `save_searchable_pdf(document, out_path)`. Copies the
  source with PyMuPDF and, for each OCR'd page, writes the recognized text
  invisibly (`render_mode=3`) at the span positions, so the output is
  Ctrl+F-searchable in any reader. Never overwrites the source.

### OCR flow

```
open PDF
  -> render + show page 1 immediately
  -> compute file hash; if cache hit: load all page text, done
  -> else: for each page, in a background worker:
       native text layer present?  -> use it, cache it
       else                        -> render page to image, OCR it, cache it
       emit progress after each page
  -> search enabled per page as its text becomes available; fully enabled
     when the sweep finishes
```

The background worker is a single `QThread` (RapidOCR's engine is a
process-global singleton and not thread-safe — same constraint as the memo
tool). The user can view/scroll freely while it runs; OCR of the page
currently on screen is prioritized (jump it to the front of the queue).

### Data / cache model

```
%LOCALAPPDATA%\PdfOcrReader\
  config.toml            -> { last_dir, dpi, theme }   (created on first run)
  cache\
    <sha256>.json        -> { "path": "...", "page_count": N, "engine": "rapidocr",
                              "dpi": 300, "created_at": "...",
                              "pages": { "0": [ {"text","bbox"}... ], ... } }
```

No document content is stored anywhere else; the cache is local and can be
deleted at any time.

## UI

One resizable window:

- **Top bar**: Open… · page N of M (editable) · zoom − / fit / + · a
  search field.
- **Left**: vertical thumbnail strip (click to jump). Collapsible.
- **Center**: the current page, rendered. Matched text drawn as a
  translucent yellow rectangle over the OCR bbox. Scroll / arrow keys /
  Page Up-Down move pages.
- **Right (when a search is active)**: results list — "p.12  …feed to the
  37-R-101B reactor was…" — click to jump + highlight.
- **Bottom**: OCR progress ("OCR 34 / 118 pages") while the sweep runs;
  hidden when idle or cache-loaded.
- **Menu**: Open, Save searchable copy…, Clear OCR cache, About.

No fake toolbars or ribbon — a plain, fast utility window.

## Error handling

- Corrupt / password-protected / not-a-PDF → a clear message, no crash.
- A page that fails to render or OCR → that page shows "could not read this
  page", the rest keep working; the failure is logged in the cache entry.
- OCR engine fails to initialize (rare) → the app still works as a plain
  PDF viewer; search is limited to any native text layer, with a one-line
  notice.
- Cache directory unwritable → OCR still works for the session, just not
  persisted; a one-line notice.

## Testing

- Core functions (renderer, textlayer, ocr, document, cache, search,
  exporter) unit-tested against small fixtures: a born-digital PDF (has a
  text layer), a synthetic "scanned" PDF (an image of known text, no text
  layer), a corrupt file.
- `search` tested for ranking, AND-of-terms, snippet windowing, bbox
  return.
- `exporter` output re-opened and asserted to contain the expected text via
  `page.get_text()`.
- One end-to-end test: open the synthetic scan, run the OCR sweep
  (RapidOCR real), search a known word, assert the right page + a non-empty
  bbox.
- A test that the core package imports with PySide6 absent.
- GUI exercised manually per phase (no automated UI tests), same as the
  memo tool.

## Delivery phasing

1. **Phase 1 — Core: open, render, native text, search.** No OCR yet.
   `renderer`, `textlayer`, `document` (native-only), `search`, cache
   scaffold. CLI smoke: open a born-digital PDF, print search hits.
2. **Phase 2 — OCR.** `ocr` (RapidOCR + bboxes), background sweep in
   `document`, the JSON cache, native-or-OCR per page. CLI smoke: OCR a
   real scanned PDF, search it, confirm page + bbox.
3. **Phase 3 — GUI.** PySide6 window: page view, thumbnails, search bar +
   results, highlight boxes, progress bar, Open / recent dir. Manual
   verification against real scans.
4. **Phase 4 — Searchable-PDF export + polish.** "Save searchable copy…",
   Clear cache, config.toml, About, keyboard nav, zoom.
5. **Phase 5 — Installer.** PyInstaller spec + Inno Setup, reusing the
   Refinery Doc Organizer packaging setup (clean-venv build, per-user
   install, bilingual first-run note).

Each phase is independently useful (Phase 1 alone is a fast PDF viewer
with search over born-digital PDFs).

## Reuse from Refinery Doc Organizer

`C:\Development\Oil and Gas\refinery-doc-organizer` — copy and adapt, don't
depend on it:

- `src/doc_organizer/ocr.py` → the RapidOCR wrapper (add bbox return).
- `src/doc_organizer/extractor.py` `_extract_pdf` → the native-text /
  render-to-pixmap logic.
- `packaging/` → the whole PyInstaller spec + Inno Setup script pattern,
  including the "build from a clean venv" rule and the bilingual README.
- `src/doc_organizer/gui/workers.py` → the `QThread` worker + progress
  signal pattern.

## Configuration

`config.toml` (created on first run): `last_dir` (remember the Open
folder), `dpi` (OCR render resolution, default 300), `theme`. No paths to
configure — it is an ad-hoc reader.

## Open items for later

- OCR quality knobs (deskew, contrast) if real scans come out poor —
  revisit after Phase 2 validation against actual documents.
- Batch mode ("make this whole folder searchable") — easy to add on top of
  the exporter later; not in the initial scope.
- Larger-than-RAM PDFs (thousands of pages) — the memo tool showed these
  exist; the OCR sweep already streams page by page, but the thumbnail
  strip may need windowing. Revisit if it comes up.
