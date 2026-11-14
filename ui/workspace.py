import math
from itertools import count

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMenu,
    QToolButton,
)

from core.roi import apply_roi
from ui.pages import GLUE_GAP

HINT = (
    "Open a hologram from the Static reconstruction tab\n\n"
    "Wheel: zoom view    Drag background: pan view\n"
    "Drag image: move it (it snaps to the edges of the others)\n"
    "Ctrl+wheel: scale image    Shift+wheel: rotate image\n"
    "Double-click: reset image (or fit view if on background)\n"
    "Right-click: delete, ROI, save, arrange"
)

SNAP_PIXELS = 10  # snapping distance on screen, whatever the zoom is


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
    """An image on the canvas: movable, rotatable and scalable around its
    center, and snapping to the edges of the other images while dragged.

    `array` is the data behind the pixmap (what ROIs are cut from). A derived
    image (an ROI) also knows its `source` image and the `derive` function that
    recomputes it, so it follows the source when that updates (real time).
    `auto` is True while the workspace is free to place the image in the grid;
    it becomes False once the user drags it somewhere.
    """

    def __init__(self, name, array, pixmap, source=None, derive=None):
        super().__init__()
        self.name = name
        self.array = array
        self.source = source
        self.derive = derive
        self.auto = True
        self._dragging = False
        self._press_pos = QPointF()
        self.setFlags(
            QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.set_pixmap(pixmap)

    def set_pixmap(self, pixmap: QPixmap):
        self.setPixmap(pixmap)
        # Rotation and scale act around the center of the image
        self.setTransformOriginPoint(self.boundingRect().center())

    def reset_transform(self):
        self.setRotation(0)
        self.setScale(1)

    # ---- dragging and snapping ----------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._press_pos = self.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self._dragging:
            self._dragging = False
            if self.pos() != self._press_pos:
                self.auto = False  # the user placed it: leave it where it is

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self._dragging and self.scene() is not None:
            value = value + self._snap_offset(value - self.pos())
        return super().itemChange(change, value)

    def _snap_offset(self, delta: QPointF) -> QPointF:
        """Shift that makes an edge of this image (once moved by `delta`) meet
        an edge of another one: butted against it (with the glue gap) or
        flush with it. X and Y snap independently, the nearest edge wins."""
        views = self.scene().views()
        threshold = views[0].snap_distance() if views else SNAP_PIXELS
        rect = self.sceneBoundingRect().translated(delta)
        best_x = best_y = None

        for other in self.scene().items():
            if other is self or not isinstance(other, ImageItem):
                continue
            o = other.sceneBoundingRect()
            candidates_x = ((rect.left(), (o.left(), o.right() + GLUE_GAP)),
                            (rect.right(), (o.right(), o.left() - GLUE_GAP)))
            candidates_y = ((rect.top(), (o.top(), o.bottom() + GLUE_GAP)),
                            (rect.bottom(), (o.bottom(), o.top() - GLUE_GAP)))
            for mine, targets in candidates_x:
                for target in targets:
                    d = target - mine
                    if abs(d) <= threshold and (best_x is None or abs(d) < abs(best_x)):
                        best_x = d
            for mine, targets in candidates_y:
                for target in targets:
                    d = target - mine
                    if abs(d) <= threshold and (best_y is None or abs(d) < abs(best_y)):
                        best_y = d
        return QPointF(best_x or 0.0, best_y or 0.0)


class RoiToolbar(QFrame):
    """Small floating toolbar shown after the second ROI point."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setStyleSheet(
            "RoiToolbar { background: #2b2b2b; border: 1px solid #666; border-radius: 4px; }"
            "QToolButton { color: white; padding: 3px 8px; border: none; }"
            "QToolButton:hover { background: #454545; }"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(2)
        self.accept_button = QToolButton(text="✔ Create ROI image")
        self.redo_button = QToolButton(text="↺ Redo")
        self.cancel_button = QToolButton(text="✖ Cancel")
        for button in (self.accept_button, self.redo_button, self.cancel_button):
            layout.addWidget(button)
        self.hide()


class Workspace(QGraphicsView):
    """Infinite canvas for any number of images.

    * New images go to a grid (cells as big as the biggest image, filled top to
      bottom, then left to right); dragging an image pins it where you drop it.
    * Right-click: delete / save / ROI on an image; arrange / fit on the background.
    * ROI: pick rectangle or circle, click two points, confirm in the floating
      toolbar. The new image has the size of the source, zero outside the region.
    """

    image_removed = Signal(str)  # name: the USER deleted it (pages react to this)

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
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)  # ROI preview follows the cursor

        self._items: dict[str, ImageItem] = {}
        self._hint = None
        self._show_hint()

        # ROI tool state and its two overlay widgets
        self._roi = None
        self._status = QLabel(self.viewport())
        self._status.setStyleSheet(
            "background: rgba(20, 20, 20, 200); color: white; padding: 4px 8px; border-radius: 3px;")
        self._status.move(8, 8)
        self._status.hide()
        self._roi_bar = RoiToolbar(self.viewport())
        self._roi_bar.accept_button.clicked.connect(self._roi_accept)
        self._roi_bar.redo_button.clicked.connect(self._roi_redo)
        self._roi_bar.cancel_button.clicked.connect(self.cancel_roi)

    # ---- API used by the pages ------------------------------------------
    def show_image(self, name: str, array: np.ndarray):
        """Show an array on the canvas. Same name -> update in place, keeping its
        position, rotation and scale (useful for real time). ROI images made
        from it are recomputed."""
        pixmap = array_to_pixmap(array)
        item = self._items.get(name)
        if item is None:
            self._add_item(name, array, pixmap)
            return
        resized = item.pixmap().size() != pixmap.size()
        item.set_pixmap(pixmap)
        item.array = array
        self._refresh_dependents(name, array)
        if resized:
            self.arrange()

    def show_reconstruction(self, name: str, array: np.ndarray, parent=None):
        """Kept so older code keeps working: every image is independent now."""
        self.show_image(name, array)

    def remove_image(self, name: str):
        """Remove an image (no signal: this is for the code, not the user)."""
        item = self._items.pop(name, None)
        if item is None:
            return
        if self._roi is not None and self._roi["item"] is item:
            self.cancel_roi()
        for other in self._items.values():  # images derived from it keep their pixels
            if other.source == name:
                other.source = other.derive = None
        self.scene().removeItem(item)
        if self._items:
            self.arrange()
        else:
            self._show_hint()

    def arrange(self, reset: bool = False):
        """Put the free images in a grid. Cells are as big as the biggest image;
        they fill top to bottom, then left to right, with as many rows as makes
        the grid look like the window. Images the user moved stay where they
        are (cells they cover are skipped). reset=True frees all of them."""
        items = list(self._items.values())
        if reset:
            for item in items:
                item.auto = True
        free = [item for item in items if item.auto]
        if not free:
            return
        pinned = [item.sceneBoundingRect() for item in items if not item.auto]

        rects = [item.sceneBoundingRect() for item in items]
        cell_w = max(r.width() for r in rects) + GLUE_GAP
        cell_h = max(r.height() for r in rects) + GLUE_GAP

        view = self.viewport().size()
        view_aspect = view.width() / max(1, view.height())
        n = len(free)

        def badness(rows):  # grid shaped like the window, without many empty cells
            columns = math.ceil(n / rows)
            shape = abs(math.log((columns * cell_w) / (rows * cell_h) / view_aspect))
            empty = (rows * columns - n) / (rows * columns)
            return shape + 1.5 * empty

        rows = min(range(1, n + 1), key=badness)

        def cells():
            for column in count():
                for row in range(rows):
                    yield QRectF(column * cell_w, row * cell_h, cell_w, cell_h)

        generator = cells()
        for item in free:
            for cell in generator:
                if not any(cell.intersects(p) for p in pinned):
                    break
            top_left = item.sceneBoundingRect().topLeft()
            item.setPos(item.pos() + cell.topLeft() - top_left)

    def fit_to(self, item=None):
        target = item.sceneBoundingRect() if item is not None else self._content_rect()
        if target.isValid() and not target.isNull():
            self.fitInView(target, Qt.KeepAspectRatio)

    def snap_distance(self) -> float:
        """Snapping distance in scene units (constant on screen)."""
        return SNAP_PIXELS / max(self.transform().m11(), 1e-6)

    # ---- internals --------------------------------------------------------
    def _show_hint(self):
        self._hint = self.scene().addText(HINT)
        self._hint.setDefaultTextColor(QColor(200, 200, 200))
        rect = self._hint.boundingRect()
        self._hint.setPos(-rect.width() / 2, -rect.height() / 2)

    def _content_rect(self) -> QRectF:
        rect = QRectF()
        for item in self._items.values():
            rect = rect.united(item.sceneBoundingRect())
        return rect

    def _add_item(self, name, array, pixmap, source=None, derive=None):
        if self._hint is not None:
            self.scene().removeItem(self._hint)
            self._hint = None
        item = ImageItem(name, array, pixmap, source, derive)
        self.scene().addItem(item)
        self._items[name] = item
        self.arrange()
        visible = self.mapFromScene(item.sceneBoundingRect()).boundingRect()
        if not self.viewport().rect().contains(visible):
            self.fit_to()  # only move the view if the new image is not in sight
        return item

    def _refresh_dependents(self, name, array):
        for item in self._items.values():
            if item.source == name and item.derive is not None:
                item.array = item.derive(array)
                item.set_pixmap(array_to_pixmap(item.array))

    def _unique_name(self, base: str) -> str:
        return next(f"{base} {n}" for n in count(1) if f"{base} {n}" not in self._items)

    def _image_at(self, pos):
        item = self.itemAt(pos)
        while item is not None and not isinstance(item, ImageItem):
            item = item.parentItem()
        return item

    # ---- context menu -----------------------------------------------------
    def contextMenuEvent(self, event):
        if self._roi is not None:  # right-click while drawing = cancel
            self.cancel_roi()
            event.accept()
            return
        item = self._image_at(event.pos())
        menu = self.image_menu(item) if item is not None else self.background_menu()
        menu.exec(event.globalPos())
        event.accept()

    def image_menu(self, item: ImageItem) -> QMenu:
        menu = QMenu(self)
        menu.addAction(item.name).setEnabled(False)
        roi_menu = menu.addMenu("Region of interest")
        roi_menu.addAction("Rectangle").triggered.connect(lambda: self.start_roi(item, "rect"))
        roi_menu.addAction("Circle").triggered.connect(lambda: self.start_roi(item, "circle"))
        menu.addAction("Save image...").triggered.connect(lambda: self._save(item))
        menu.addSeparator()
        menu.addAction("Delete").triggered.connect(lambda: self._delete(item.name))
        return menu

    def background_menu(self) -> QMenu:
        menu = QMenu(self)
        arrange = menu.addAction("Arrange images in grid")
        arrange.triggered.connect(lambda: (self.arrange(reset=True), self.fit_to()))
        fit = menu.addAction("Fit all images")
        fit.triggered.connect(lambda: self.fit_to())
        arrange.setEnabled(bool(self._items))
        fit.setEnabled(bool(self._items))
        return menu

    def _delete(self, name: str):
        self.remove_image(name)
        self.image_removed.emit(name)

    def _save(self, item: ImageItem):
        path, _ = QFileDialog.getSaveFileName(self, "Save image", f"{item.name}.png", "PNG (*.png)")
        if path:
            item.pixmap().save(path)

    # ---- ROI tool -----------------------------------------------------------
    def start_roi(self, item: ImageItem, kind: str):
        """kind: 'rect' (two opposite corners) or 'circle' (center, then a
        point of the circumference)."""
        self.cancel_roi()
        self._roi = {"item": item, "kind": kind, "p1": None, "p2": None, "preview": None}
        self.setDragMode(QGraphicsView.NoDrag)
        self.viewport().setCursor(Qt.CrossCursor)
        self.setFocus()
        first = "first corner" if kind == "rect" else "center"
        self._set_status(f"ROI on “{item.name}”: click the {first}   (Esc / right-click: cancel)")

    def cancel_roi(self):
        roi, self._roi = self._roi, None
        if roi is None:
            return
        preview = roi["preview"]
        if preview is not None and preview.scene() is not None:
            self.scene().removeItem(preview)
        self._roi_bar.hide()
        self._set_status("")
        self.viewport().unsetCursor()
        self.setDragMode(QGraphicsView.ScrollHandDrag)

    def _set_status(self, text: str):
        self._status.setText(text)
        self._status.setVisible(bool(text))
        self._status.adjustSize()

    def _item_point(self, item: ImageItem, view_pos, clamp: bool) -> QPointF:
        p = item.mapFromScene(self.mapToScene(view_pos))
        if clamp:
            rect = item.boundingRect()
            p = QPointF(min(max(p.x(), 0.0), rect.width()), min(max(p.y(), 0.0), rect.height()))
        return p

    def _roi_spec(self):
        roi = self._roi
        p1, p2 = roi["p1"], roi["p2"]
        if roi["kind"] == "rect":
            return ("rect", min(p1.x(), p2.x()), min(p1.y(), p2.y()), max(p1.x(), p2.x()), max(p1.y(), p2.y()))
        return ("circle", p1.x(), p1.y(), math.hypot(p2.x() - p1.x(), p2.y() - p1.y()))

    def _update_preview(self, current: QPointF):
        roi = self._roi
        if roi["preview"] is None:
            shape = QGraphicsRectItem if roi["kind"] == "rect" else QGraphicsEllipseItem
            preview = shape(roi["item"])  # child of the image: follows it when moved
            pen = QPen(QColor(255, 210, 0), 1.5, Qt.DashLine)
            pen.setCosmetic(True)  # constant width on screen
            preview.setPen(pen)
            preview.setBrush(QBrush(QColor(255, 210, 0, 40)))
            preview.setZValue(10)
            roi["preview"] = preview
        p1 = roi["p1"]
        if roi["kind"] == "rect":
            roi["preview"].setRect(QRectF(p1, current).normalized())
        else:
            r = math.hypot(current.x() - p1.x(), current.y() - p1.y())
            roi["preview"].setRect(QRectF(p1.x() - r, p1.y() - r, 2 * r, 2 * r))

    def _roi_press(self, event):
        roi = self._roi
        pos = event.position().toPoint()
        if roi["p1"] is None or roi["p2"] is not None:  # first point (or starting over)
            roi["p1"] = self._item_point(roi["item"], pos, clamp=True)
            roi["p2"] = None
            self._roi_bar.hide()
            self._update_preview(roi["p1"])
            second = "opposite corner" if roi["kind"] == "rect" else "point on the circle"
            self._set_status(f"Click the {second}")
        else:
            roi["p2"] = self._item_point(roi["item"], pos, clamp=roi["kind"] == "rect")
            self._update_preview(roi["p2"])
            self._set_status("Create the ROI image, redo, or cancel")
            self._show_roi_bar(pos)

    def _roi_move(self, event):
        roi = self._roi
        if roi["p1"] is not None and roi["p2"] is None:  # rubber band after the first point
            point = self._item_point(roi["item"], event.position().toPoint(), clamp=roi["kind"] == "rect")
            self._update_preview(point)

    def _show_roi_bar(self, pos):
        bar, area = self._roi_bar, self.viewport().rect()
        bar.adjustSize()
        x = min(max(pos.x() + 12, 4), max(4, area.width() - bar.width() - 4))
        y = min(max(pos.y() + 12, 4), max(4, area.height() - bar.height() - 4))
        bar.move(x, y)
        bar.show()
        bar.raise_()

    def _roi_redo(self):
        roi = self._roi
        if roi is None:
            return
        roi["p1"] = roi["p2"] = None
        if roi["preview"] is not None:
            self.scene().removeItem(roi["preview"])
            roi["preview"] = None
        self._roi_bar.hide()
        self._set_status("Click the first point again")

    def _roi_accept(self):
        roi = self._roi
        if roi is None or roi["p2"] is None:
            return
        spec = self._roi_spec()
        degenerate = (spec[3] <= spec[1] or spec[4] <= spec[2]) if spec[0] == "rect" else spec[3] <= 0
        if degenerate:
            self._roi_redo()
            self._set_status("That region is empty. Click the first point again")
            return
        source = roi["item"]
        self.cancel_roi()

        def derive(array, spec=spec):
            return apply_roi(array, spec)

        array = derive(source.array)
        self._add_item(self._unique_name(f"{source.name} ROI"), array, array_to_pixmap(array),
                       source=source.name, derive=derive)

    # ---- mouse and keyboard ----------------------------------------------------
    def keyPressEvent(self, event):
        if self._roi is not None and event.key() == Qt.Key_Escape:
            self.cancel_roi()
        elif self._roi is not None and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._roi_accept()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if self._roi is not None and event.button() == Qt.LeftButton:
            self._roi_press(event)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self._roi is not None:  # two quick clicks must count as two points
            self._roi_press(event)
            event.accept()
            return
        item = self._image_at(event.position().toPoint())
        if item is not None:
            item.reset_transform()
        elif self._items:
            self.fit_to()
        event.accept()

    def mouseMoveEvent(self, event):
        if self._roi is not None:
            self._roi_move(event)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._roi is not None:
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta().y() or event.angleDelta().x()  # Shift may swap axes
        if delta == 0:
            return
        steps = delta / 120.0
        mods = event.modifiers()
        item = self._image_at(event.position().toPoint())
        if mods & Qt.ControlModifier:
            if item is not None:
                item.setScale(max(0.01, item.scale() * 1.1 ** steps))
        elif mods & Qt.ShiftModifier:
            if item is not None:
                item.setRotation(item.rotation() + 5.0 * steps)
        else:
            factor = 1.15 ** steps
            self.scale(factor, factor)  # zoom the view, anchored under the mouse
        event.accept()