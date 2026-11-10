from PySide6.QtCore import QSize, Qt
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

from PySide6.QtGui import QAction
from random import choice

import sys

field_names = [
    'DLHM',
    'DHM',
    'Optical Imaging',
    'Fiber'
]

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Octopi!")

        self.strip_tab_menu = QWidget()
        self.options_menu = QWidget()
        self.workspace_menu = QWidget()

        # Strip elements
        # sb == strip button

        self.main_menu_tab = QLabel('main')
        self.settings_tab = QLabel('settings')
        self.appearance_tab = QLabel('themes')
        self.info_sb = QLabel('info')

        strip_tabs = [
            self.main_menu_tab, self.settings_tab, self.appearance_tab, self.info_sb
        ]


        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.West)
        tabs.setMovable(True)
        for tab in strip_tabs:
            tabs.addTab(tab, '!!!!!')

        layout = QHBoxLayout()

        layout.addWidget(self.strip_tab_menu)
        layout.addWidget(self.options_menu)
        layout.addWidget(self.workspace_menu)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)





