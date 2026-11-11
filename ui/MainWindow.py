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

        self.setWindowTitle("My App")

        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.West)
        tabs.setMovable(True)

        for ind, field in enumerate(field_names):
            content = QLabel()
            content.setText(field)
            tabs.addTab(content, field)

        self.setCentralWidget(tabs)





