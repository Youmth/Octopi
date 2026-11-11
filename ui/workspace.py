import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
)

HINT = (
    "Open a hologram from the Static reconstruction tab\n\n"
    "Wheel: zoom view    Drag background: pan view\n"
    "Drag image: move it    Ctrl+wheel: scale image    "
    "Shift+wheel: rotate image\n"
    "Double-click: reset image (or fit view if on background)"
)


def array_to_pixmap(array: np.ndarray) -> QPixmap:
    """2D array (any dtype) -> grayscale QPixmap, stretched to 0-255."""
    a = np.asarray(array)
    if a.dtype != np.uint8:
        a = a.astype(np.float64)
        lo, hi = a.min(), a.max()
        a = (a - lo) / (hi - lo if hi > lo else 1.0) * 255.0
        a = a.astype(np.uint8)
    a = np.ascontiguousarray(a)
    h, w = a.shape
    qimg = QImage(a.data, w, h, w, QImage.Format_Grayscale8)
    return QPixmap.fromImage(qimg)  # copies the data, so `a` can be freed


class ImageItem(QGraphicsPixmapItem):
    """An image on the canvas: movable, rotatable and scalable around its center."""

    def __init__(self, pixmap: QPixmap):
        super().__init__()
        self.setFlags(
            QGraphicsPixmapItem.ItemIsMovable | QGraphicsPixmapItem.ItemIsSelectable
        )
        self.set_pixmap(pixmap)

    def set_pixmap(self, pixmap: QPixmap):
        self.setPixmap(pixmap)
        # Rotation and scale act around the center of the image
        self.setTransformOriginPoint(self.boundingRect().center())

    def reset_transform(self):
        self.setRotation(0)
        self.setScale(1)


class Workspace(QGraphicsView):
    """Infinite canvas for images. Later: real-time frames and floating panels."""

    def __init__(self):
        super().__init__()
        scene = QGraphicsScene(self)
        # Huge scene rect so panning is not limited to the image bounds
        scene.setSceneRect(-50000, -50000, 100000, 100000)
        self.setScene(scene)

        self.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setRenderHints(QPainter.SmoothPixmapTransform)

        self._items: dict[str, ImageItem] = {}
        self._hint = scene.addText(HINT)
        self._hint.setDefaultTextColor(QColor(200, 200, 200))
        rect = self._hint.boundingRect()
        self._hint.setPos(-rect.width() / 2, -rect.height() / 2)

    # ---- API used by the pages --------------------------------------
    def show_image(self, name: str, array: np.ndarray):
        """Show an array on the canvas. Same name -> update in place,
        keeping its position, rotation and scale (useful for real time)."""
        pixmap = array_to_pixmap(array)
        item = self._items.get(name)
        if item is not None:
            item.set_pixmap(pixmap)
            return

        if self._hint is not None:
            self.scene().removeItem(self._hint)
            self._hint = None

        item = ImageItem(pixmap)
        item.setPos(QPointF(-pixmap.width() / 2, -pixmap.height() / 2))
        self.scene().addItem(item)
        self._items[name] = item
        self.fit_to(item)

    def fit_to(self, item=None):
        target = item if item is not None else self.scene().itemsBoundingRect()
        self.fitInView(target, Qt.KeepAspectRatio)

    # ---- Mouse interaction ------------------------------------------
    def wheelEvent(self, event):
        delta = event.angleDelta().y() or event.angleDelta().x()  # Shift may swap axes
        if delta == 0:
            return
        steps = delta / 120.0
        mods = event.modifiers()
        item = self.itemAt(event.position().toPoint())

        if mods & Qt.ControlModifier:
            if item is not None:
                item.setScale(max(0.01, item.scale() * 1.1**steps))
        elif mods & Qt.ShiftModifier:
            if item is not None:
                item.setRotation(item.rotation() + 5.0 * steps)
        else:
            factor = 1.15**steps
            self.scale(factor, factor)  # zoom the view, anchored under the mouse
        event.accept()

    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.position().toPoint())
        if isinstance(item, ImageItem):
            item.reset_transform()
        elif self._items:
            self.fit_to()
        event.accept()