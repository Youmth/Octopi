from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView


class Workspace(QGraphicsView):
    """Placeholder. Later: canvas with pan, zoom, rotation and overlays."""

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
        text = self.scene().addText("Workspace")
        text.setDefaultTextColor(QColor("white"))