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
        # One single QMainWindow owns EVERY dock (Techniques and all page panels),
        # so any dock can go to any side, tab with another, nest, or float.
        self.setDockNestingEnabled(True)
        self.setDockOptions(
            QMainWindow.AllowTabbedDocks
            | QMainWindow.AllowNestedDocks
            | QMainWindow.AnimatedDocks
        )

        self.techniques_dock = QDockWidget("Techniques", self)
        self.techniques_dock.setObjectName("TechniquesDock")
        self.techniques_dock.setWidget(self.tabs)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.techniques_dock)

        view_menu = self.menuBar().addMenu('View')
        view_menu.addAction(self.techniques_dock.toggleViewAction())

        for field, page_classes in PAGES.items():
            subtabs = QTabWidget()
            subtabs.setTabPosition(QTabWidget.West)
            subtabs.setMovable(True)

            for cls in page_classes:
                page = cls()
                page.image_ready.connect(self.workspace.show_image)
                page.reconstruction_ready.connect(self.workspace.show_reconstruction)
                subtabs.addTab(page, cls.title)

                for dock in page.panels:
                    self.splitDockWidget(self.techniques_dock, dock, Qt.Vertical)
                    dock.hide()
                    view_menu.addAction(dock.toggleViewAction())

            subtabs.currentChanged.connect(self._update_active_page)
            self.tabs.addTab(subtabs, field)


        self.tabs.currentChanged.connect(self._update_active_page)

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







