from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QPushButton,
    QLabel,
    QLineEdit,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QStackedLayout,
    QTabWidget,
    QWidget,
    QMenu,
)
class Page(QWidget):
    """Base class for every technique page."""
    title = "Untitled"

    # (name, 2D array): ask the workspace to display an image.
    # Same name again -> the image is updated in place.
    image_ready = Signal(str, object)


    def on_show(self):
        """Called when the page becomes visible: start timers here."""

    def on_hide(self):
        """Called when the page is hidden: stop timers, free GPU work."""

class PlaceholderPage(Page):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        for _ in range(2):
            label = QLabel()
            label.setText(self.title)
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
    def on_show(self):
        print(f"[show] {self.title}")

    def on_hide(self):
        print(f"[hide] {self.title}")
