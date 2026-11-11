from PySide6.QtWidgets import QMainWindow, QTabWidget, QDockWidget
from PySide6.QtCore import Qt
from ui.workspace import Workspace
from ui.pages import PAGES

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Octopi!")
        self._active_page = None

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.West)
        self.tabs.setMovable(True)

        self.workspace = Workspace()
        self.setCentralWidget(self.workspace)

        for field, page_classes in PAGES.items():
            subtabs = QTabWidget()
            subtabs.setTabPosition(QTabWidget.West)
            subtabs.setMovable(True)

            for cls in page_classes:
                page = cls()
                page.image_ready.connect(self.workspace.show_image)
                subtabs.addTab(page, cls.title)

            subtabs.currentChanged.connect(self._update_active_page)
            self.tabs.addTab(subtabs, field)


        self.tabs.currentChanged.connect(self._update_active_page)


        dock = QDockWidget("Techniques", self)
        dock.setWidget(self.tabs)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

        # If the dock is closed, this menu entry brings it back
        self.menuBar().addMenu("View").addAction(dock.toggleViewAction())

        self._update_active_page()

    def _update_active_page(self, *args):

        subtabs = self.tabs.currentWidget()
        page = subtabs.currentWidget() if subtabs is not None else None

        if page is self._active_page:
            return
        if self._active_page is not None:
            self._active_page.on_hide()
        self._active_page = page

        if page is not None:
            page.on_show()

    def closeEvent(self, event):
        if self._active_page is not None:
            self._active_page.on_hide()
        super().closeEvent(event)







