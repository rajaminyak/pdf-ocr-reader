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
