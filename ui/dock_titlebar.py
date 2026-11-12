from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QStyle,
    QToolButton,
    QWidget,
)


class DockTitleBar(QWidget):
    """Custom title bar for a QDockWidget, so every dock behaves the same way.

    Docked:    dragging the bar uses Qt's normal docking drag (snap to any side,
               tab, nest).
    Floating:  dragging the bar moves the window freely, anywhere, with NO
               snapping, so floating panels can overlap each other and the
               workspace. Hold Shift while dragging to use docking drag instead.
    Buttons:   float/dock toggle and close. Double-click toggles floating.
    """

    def __init__(self, dock: QDockWidget):
        super().__init__(dock)
        self.dock = dock
        self._drag_offset = None

        self.label = QLabel(dock.windowTitle())
        dock.windowTitleChanged.connect(self.label.setText)

        style = self.style()
        self.float_button = self._button(
            QStyle.SP_TitleBarNormalButton, "Float / dock", self._toggle_floating
        )
        self.close_button = self._button(
            QStyle.SP_TitleBarCloseButton, "Close", dock.close
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 2, 2)
        layout.setSpacing(2)
        layout.addWidget(self.label, 1)
        layout.addWidget(self.float_button)
        layout.addWidget(self.close_button)

        # The label must not swallow mouse events: they belong to the title bar
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents)

    def _button(self, icon, tip, slot):
        b = QToolButton(self)
        b.setIcon(self.style().standardIcon(icon))
        b.setToolTip(tip)
        b.setAutoRaise(True)
        b.setFocusPolicy(Qt.NoFocus)
        b.clicked.connect(slot)
        return b

    def _toggle_floating(self):
        self.dock.setFloating(not self.dock.isFloating())

    # ---- mouse ------------------------------------------------------
    def mousePressEvent(self, event):
        free_move = (
            event.button() == Qt.LeftButton
            and self.dock.isFloating()
            and not (event.modifiers() & Qt.ShiftModifier)
        )
        if not free_move:
            event.ignore()  # let QDockWidget do its docking drag
            return
        handle = self.dock.windowHandle()
        # Ask the OS to move the window: works on Windows, X11, Wayland, macOS
        if handle is not None and handle.startSystemMove():
            event.accept()
            return
        # Fallback: move it ourselves
        self._drag_offset = (
            event.globalPosition().toPoint() - self.dock.frameGeometry().topLeft()
        )
        event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.dock.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        if self._drag_offset is not None:
            self._drag_offset = None
            event.accept()
        else:
            event.ignore()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._toggle_floating()
            event.accept()
        else:
            event.ignore()


def install_title_bar(dock: QDockWidget):
    """Give `dock` the shared title bar and make its floating window 'sticky':
    a tool window owned by the main window, so it stays above it, never blocks
    the rest of the app and does not vanish when the app loses focus (macOS)."""
    dock.setTitleBarWidget(DockTitleBar(dock))
    dock.setAttribute(Qt.WA_MacAlwaysShowToolWindow, True)