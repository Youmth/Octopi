from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QApplication,
    QPushButton,
    QLabel,
    QLineEdit,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QMenu,
)

from PySide6.QtGui import QAction
from random import choice

import sys


# You need one (and only one) QApplication instance per application.
# Pass in sys.argv to allow command line arguments for your app.
# If you know you won't use command line arguments QApplication([]) works too.

#app = QApplication(sys.argv)
# app = QApplication([])
#
# window = QWidget()
# window.show()
#
# window2 = QPushButton('Please push meeee')
# window2.show()
#
# app.exec()

# class MainWindow(QMainWindow):
#     def __init__(self):
#         super().__init__()
#
#         self.button_checked = True
#
#         self.setWindowTitle("Octopi")
#
#         # button = QPushButton("Press Me")
#         # # self.setFixedSize(QSize(800, 600))
#         # self.setCentralWidget(button)
#
#         self.button: QPushButton = QPushButton("Press Me!")
#         # self.button.setCheckable(True)
#         self.button.setCheckable(False)
#         self.button.clicked.connect(self.on_click)
#         # self.button.clicked.connect(self.on_toggle)
#         # self.button.released.connect(self.on_release)
#         # self.button.setChecked(self.button_checked)
#
#
#         self.setCentralWidget(self.button)
#
#     def on_click(self):
#         self.button.setText("You already clicked me.")
#         self.button.setEnabled(False)
#
#         self.setWindowTitle("Octopi (Clicked)")
#
#     def on_toggle(self, checked):
#         self.button_checked = checked
#
#         print("Checked?", checked)
#
#     def on_release(self):
#         self.button_checked = self.button.isChecked()
#
#         print('Button was released', self.button_checked)


window_titles = [
    "Octopi",
    "Octopi",
    "Still Octopi",
    "Still Octopi",
    "What on earth",
    "What on earth",
    "This is surprising",
    "This is surprising",
    "Something went wrong",
]

# class MainWindow(QMainWindow):
#     def __init__(self):
#         super().__init__()
#
#         self.n_times_clicked = 0
#
#         self.setWindowTitle("Octopi!")
#
#         self.button = QPushButton("Press me!")
#
#         self.button.clicked.connect(self.on_click)
#
#         self.windowTitleChanged.connect(self.on_window_title_changed)
#
#         self.setCentralWidget(self.button)
#
#     def on_click(self):
#         print("Clicked")
#         new_window_title = choice(window_titles)
#         print("Setting title: %s" % new_window_title)
#         self.setWindowTitle(new_window_title)
#
#     def on_window_title_changed(self, title):
#         print("Window title changed: %s" % title)
#
#         if title == window_titles[-1]:
#             self.button.setDisabled(True)

# class MainWindow(QMainWindow):
#     def __init__(self):
#         super().__init__()
#         self.setWindowTitle('Octopi!')
#
#         self.label = QLabel()
#
#         self.input_ = QLineEdit()
#         self.input_.textChanged.connect(self.label.setText)
#
#         self.button = QPushButton('Press me!')
#
#         layout = QVBoxLayout()
#         layout.addWidget(self.input_)
#         layout.addWidget(self.label)
#         layout.addWidget(self.button)
#
#         container = QWidget()
#         container.setLayout(layout)
#
#         self.setCentralWidget(container)

# class MainWindow(QMainWindow):
#     def __init__(self):
#         super().__init__()
#         self.label = QLabel("Click this window")
#         self.setMouseTracking(True)
#         self.label.setMouseTracking(True)
#         self.setCentralWidget(self.label)
#
#     def mouseMoveEvent(self, e):
#         self.label.setText("mouseMoveEvent")
#
#     def mousePressEvent(self, e):
#         self.label.setText("mousePressEvent")
#
#     def mouseReleaseEvent(self, e):
#         self.label.setText("mouseReleaseEvent")
#
#     def mouseDoubleClickEvent(self, e):
#         self.label.setText("mouseDoubleClickEvent")


# class MainWindow(QMainWindow):
#     def __init__(self):
#         super().__init__()
#         self.label = QLabel("Click in this window")
#         self.setMouseTracking(True)
#         self.label.setMouseTracking(True)
#         self.setCentralWidget(self.label)
#
#     def mouseMoveEvent(self, e):
#         self.label.setText("mouseMoveEvent")
#
#     def mousePressEvent(self, e):
#         if e.button() == Qt.MouseButton.LeftButton:
#             # handle the left-button press in here
#             self.label.setText("mousePressEvent LEFT")
#
#         elif e.button() == Qt.MouseButton.MiddleButton:
#             # handle the middle-button press in here.
#             self.label.setText("mousePressEvent MIDDLE")
#
#         elif e.button() == Qt.MouseButton.RightButton:
#             # handle the right-button press in here.
#             self.label.setText("mousePressEvent RIGHT")
#
#     def mouseReleaseEvent(self, e):
#         if e.button() == Qt.MouseButton.LeftButton:
#             self.label.setText("mouseReleaseEvent LEFT")
#
#         elif e.button() == Qt.MouseButton.MiddleButton:
#             self.label.setText("mouseReleaseEvent MIDDLE")
#
#         elif e.button() == Qt.MouseButton.RightButton:
#             self.label.setText("mouseReleaseEvent RIGHT")
#
#     def mouseDoubleClickEvent(self, e):
#         if e.button() == Qt.MouseButton.LeftButton:
#             self.label.setText("mouseDoubleClickEvent LEFT")
#
#         elif e.button() == Qt.MouseButton.MiddleButton:
#             self.label.setText("mouseDoubleClickEvent MIDDLE")
#
#         elif e.button() == Qt.MouseButton.RightButton:
#             self.label.setText("mouseDoubleClickEvent RIGHT")

# class MainWindow(QMainWindow):
#     def __init__(self):
#         super().__init__()
#
#     def contextMenuEvent(self, e):
#         context = QMenu(self)
#         context.addAction(QAction("test 1", self))
#         context.addAction(QAction("test 2", self))
#         context.addAction(QAction("test 3", self))
#         context.exec(e.globalPos())

# class MainWindow(QMainWindow):
#     def __init__(self):
#         super().__init__()
#
#         self.setContextMenuPolicy(Qt.CustomContextMenu)
#         self.customContextMenuRequested.connect(self.on_context_menu)
#
#     def on_context_menu(self, pos):
#         context = QMenu(self)
#         context.addAction(QAction("test 1", self))
#         context.addAction(QAction("test 2", self))
#         context.addAction(QAction("test 3", self))
#         context.exec(self.mapToGlobal(pos))