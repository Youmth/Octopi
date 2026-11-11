from PySide6.QtWidgets import QFileDialog, QLabel, QPushButton, QVBoxLayout

from core.io import load_grayscale
from .base import Page


class DLHMStatic(Page):
    title = "Static reconstruction"

    def __init__(self):
        super().__init__()
        self.hologram = None

        self.open_button = QPushButton("Open hologram...")
        self.open_button.clicked.connect(self.open_hologram)

        self.info = QLabel("No hologram loaded")
        self.info.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.open_button)
        layout.addWidget(self.info)
        layout.addStretch()

    def open_hologram(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open hologram",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)",
        )
        if not path:
            return
        self.hologram = load_grayscale(path)
        h, w = self.hologram.shape
        self.info.setText(f"{path}\n{w} x {h} px")
        self.image_ready.emit("hologram", self.hologram)