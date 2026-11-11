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

tab_titles = {
    # The tabs are the fields of study
    # The subtabs are the techniques to be used
    'DLHM':[
        'Real time reconstruction',
        'Static reconstruction',
        'Contrast real time reconstruction'
    ],
    'DHM':[
        'DHM',
    ],
    'Optical Imaging':[
        'Optical Imaging',
    ],
    'Fiber':[
        'Fiber'
    ]
}

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Octopi!")

        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.West)
        tabs.setMovable(True)


        for field, techniques in tab_titles.items():
            # In this case, the content of the tab is another tab widget
            subtabs = QTabWidget()
            subtabs.setTabPosition(QTabWidget.West)
            subtabs.setMovable(True)

            for technique in techniques:
                content = QLabel()
                content.setText(technique)
                subtabs.addTab(content, technique)

            tabs.addTab(subtabs, field)



        self.setCentralWidget(tabs)





