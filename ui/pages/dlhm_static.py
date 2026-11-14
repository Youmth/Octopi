from PySide6.QtWidgets import QFileDialog, QLabel, QPushButton, QVBoxLayout

from core.io import load_grayscale
from ui.pages.dlhm_base import DLHMPage


class DLHMStatic(DLHMPage):
    """DLHM on a hologram loaded from disk."""
    title = "Static reconstruction"

    def __init__(self):
        super().__init__()

        self.open_button = QPushButton("Open hologram...")
        self.open_button.clicked.connect(self.open_hologram)

        self.info = QLabel("No hologram loaded")
        self.info.setWordWrap(True)
        self.info_recon.setText("No reconstruction has been performed")
        self.info_recon.setWordWrap(True)

        self.reconstruct_button = QPushButton("Reconstruct from current parameters.")
        self.reconstruct_button.clicked.connect(self.reconstruct_hologram)

        layout = QVBoxLayout(self)
        layout.addWidget(self.open_button)
        layout.addWidget(self.info)
        layout.addWidget(self.reconstruct_button)
        layout.addWidget(self.common_widget)  # live toggle, reference, recording, result info
        layout.addStretch()

    def _on_live_changed(self, checked: bool):
        self.reconstruct_button.setEnabled(not checked)

    def _on_hologram_removed(self):
        self.info.setText("No hologram loaded")

    def open_hologram(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open hologram", "", "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)")
        if not path:
            return
        hologram = load_grayscale(path)
        h, w = hologram.shape
        self.info.setText(f"{path}\n{w} x {h} px")
        self.set_hologram(hologram)