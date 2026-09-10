from __future__ import annotations

from dataclasses import dataclass, field

BBox = tuple[float, float, float, float]  # (x0, y0, x1, y1)


@dataclass(frozen=True)
class Span:
    text: str
    bbox: BBox

    def as_dict(self) -> dict:
        return {"text": self.text, "bbox": list(self.bbox)}

    @classmethod
    def from_dict(cls, d: dict) -> "Span":
        x0, y0, x1, y1 = d["bbox"]
        return cls(text=d["text"], bbox=(float(x0), float(y0), float(x1), float(y1)))


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
