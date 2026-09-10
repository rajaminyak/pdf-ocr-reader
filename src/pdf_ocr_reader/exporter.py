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
