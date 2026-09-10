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
