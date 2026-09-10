from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QImage, QPen, QPixmap
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

_HL_BRUSH = QBrush(QColor(255, 214, 0, 70))
_HL_PEN = QPen(QColor(230, 170, 0, 160))


def scene_rect_for_span(bbox, *, source_dpi: int, render_dpi: int):
    """Scale a span bbox from its source space to rendered-page pixel space.

    source_dpi = 72 for native text (PDF points), ocr.OCR_DPI for OCR pixels.
    Returns (x, y, w, h) for a QRectF in the rendered page's coordinate space.
    """
    x0, y0, x1, y1 = bbox
    k = render_dpi / source_dpi
    return (x0 * k, y0 * k, (x1 - x0) * k, (y1 - y0) * k)


class PageGraphicsView(QGraphicsView):
    def __init__(self) -> None:
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self._pixmap_item = None

    def show_page(self, png_bytes: bytes) -> None:
        image = QImage.fromData(QByteArray(png_bytes), "PNG")
        scene = self.scene()
        scene.clear()
        self._pixmap_item = scene.addPixmap(QPixmap.fromImage(image))
        scene.setSceneRect(QRectF(image.rect()))
        self.resetTransform()
        self.fit()

    def set_highlights(self, rects) -> None:
        for item in list(self.scene().items()):
            if item is not self._pixmap_item:
                self.scene().removeItem(item)
        for x, y, w, h in rects:
            self.scene().addRect(QRectF(x, y, w, h), _HL_PEN, _HL_BRUSH)

    def zoom(self, factor: float) -> None:
        self.scale(factor, factor)

    def fit(self) -> None:
        if self._pixmap_item is not None:
            self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)
