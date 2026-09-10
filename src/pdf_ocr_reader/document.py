from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import datetime, timezone

import fitz

from pdf_ocr_reader import cache, ocr, renderer, textlayer
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
        self.ocr_dpi = ocr.OCR_DPI
        self._ocr_pages: dict[int, list[Span]] = {}
        self._ocr_errors: set[int] = set()
        self._load_cache()

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

    # ---------- text ----------

    def page_spans(self, page_index: int) -> list[Span]:
        native = textlayer.native_page_spans(self._doc[page_index])
        if native is not None:
            return native
        if page_index in self._ocr_pages:
            return self._ocr_pages[page_index]
        spans = self._ocr_page(page_index)
        self._ocr_pages[page_index] = spans
        self._persist_cache()
        return spans

    def full_page_text(self, page_index: int) -> str:
        return " ".join(s.text for s in self.page_spans(page_index))

    def has_text_layer(self, page_index: int) -> bool:
        return textlayer.native_page_spans(self._doc[page_index]) is not None

    # ---------- OCR ----------

    def _ocr_page(self, page_index: int) -> list[Span]:
        try:
            rendered = renderer.render_page(self._doc[page_index], dpi=self.ocr_dpi)
            return ocr.ocr_image(rendered.png_bytes)
        except ocr.OcrError:
            self._ocr_errors.add(page_index)
            return []

    def _pages_needing_ocr(self) -> list[int]:
        pending = []
        for i in range(self.page_count):
            if i in self._ocr_pages:
                continue
            if textlayer.native_page_spans(self._doc[i]) is not None:
                continue
            pending.append(i)
        return pending

    def ocr_all(self, progress: Callable[[int, int], None] | None = None) -> None:
        pending = self._pages_needing_ocr()
        total = len(pending)
        for done, page_index in enumerate(pending, start=1):
            self._ocr_pages[page_index] = self._ocr_page(page_index)
            self._persist_cache()
            if progress is not None:
                progress(done, total)

    # ---------- cache ----------

    def _load_cache(self) -> None:
        payload = cache.read(self.content_hash)
        if not payload or payload.get("ocr_dpi") != self.ocr_dpi:
            return
        errored = set(payload.get("errors", []))
        for key, raw_spans in payload.get("pages", {}).items():
            spans = [Span.from_dict(d) for d in raw_spans]
            self._ocr_pages[int(key)] = spans
            if not spans and key in errored:
                self._ocr_errors.add(int(key))

    def _persist_cache(self) -> None:
        cache.write(
            self.content_hash,
            {
                "path": self.path,
                "page_count": self.page_count,
                "ocr_dpi": self.ocr_dpi,
                "engine": "rapidocr",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "pages": {str(i): [s.as_dict() for s in v] for i, v in self._ocr_pages.items()},
                "errors": [str(i) for i in sorted(self._ocr_errors)],
            },
        )

    # ---------- lifecycle ----------

    def close(self) -> None:
        self._doc.close()

    def __enter__(self) -> "Document":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
