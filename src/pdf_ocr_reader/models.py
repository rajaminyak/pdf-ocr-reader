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
