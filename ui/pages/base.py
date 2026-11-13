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
    QDockWidget,
    QMenu,
)
from ui.dock_titlebar import install_title_bar


class Page(QWidget):
    """Base class for every technique page."""
    title = "Untitled"

    # (name, 2D array): ask the workspace to display an image.
    # Same name again -> the image is updated in place.
    image_ready = Signal(str, object)
    reconstruction_ready = Signal(str, object)

    def __init__(self):
        super().__init__()
        # Docks created by this page. MainWindow places them in the DockHost
        self.panels: list[QDockWidget] = []
        self._panels_to_restore: list[QDockWidget] = []

    def on_show(self):
        """Called when the page becomes visible: start timers here."""
        for dock in self._panels_to_restore:
            dock.show()

    def on_hide(self):
        """Called when the page is hidden: stop timers, free GPU work."""
        self._panels_to_restore = [d for d in self.panels if not d.isHidden()]
        for dock in self.panels:
            dock.hide()

    def add_panel(self, title:str, widget: QWidget) -> QDockWidget:
        """Wrap 'widget' in a movvable dock that belongs to this page.
        The dock is NOT put in this page's layout (a QDockWidget only docks inside a MainWindow;
        Mainwindow moves it into the DockHost."""
        dock = QDockWidget(title)
        dock.setObjectName(f"{type(self).__name__}.{title}")
        dock.setWidget(widget)
        install_title_bar(dock)
        self.panels.append(dock)
        self._panels_to_restore.append(dock)
        return dock

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
