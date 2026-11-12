from PySide6.QtWidgets import QFileDialog, QLabel, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QCheckBox, QDockWidget
from PySide6.QtCore import Qt

from core.io import load_grayscale
from .base import Page
from core.reconstruction import reconstruct

import numpy as np


class DLHMStatic(Page):
    title = "Static reconstruction"

    MODES = {
        'squared' : ('Intensity', True),
        'phase': ('Phase', False),
    }

    def __init__(self):
        super().__init__()
        self.hologram = None
        self.reconstruction = None
        self.input_dict = {
            'image':None,
            'squared':None,
            'phase':None,
            'algorithm': None,
            'r': None,
            'wavelength': None,
            'dxy': None,
            'scale_factor': None,
        }

        self.open_button = QPushButton("Open hologram...")
        self.open_button.clicked.connect(self.open_hologram)

        self.reconstruct_button = QPushButton("Reconstruct from current parameters.")
        self.reconstruct_button.clicked.connect(self.reconstruct_hologram)

        # Checkbox panel: lives in a dock, not in this page's layout.
        # Each entry: input_dict key -> (label, default state)
        self.mode_boxes: dict[str, QCheckBox] = {}

        mode_widget = QWidget()
        mode_layout = QVBoxLayout()

        for key, (label, default) in self.MODES.items():
            box = QCheckBox(label)
            box.setChecked(default)
            self.input_dict[key] = default
            box.toggled.connect(lambda checked, k=key:self.input_dict.__setitem__(k, checked))
            self.mode_boxes[key] = box
            mode_layout.addWidget(box)
        mode_layout.addStretch()

        mode_widget.setLayout(mode_layout)

        self.mode_dock = self.add_panel("Mode", mode_widget)

        self.info = QLabel("No hologram loaded")
        self.info.setWordWrap(True)

        self.info_recon = QLabel("No reconstruction has been performed")
        self.info_recon.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.open_button)
        layout.addWidget(self.info)
        layout.addWidget(self.reconstruct_button)
        layout.addWidget(self.info_recon)
        layout.addWidget(self.mode_dock)

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


    def reconstruct_hologram(self):
        recon_dict = {
            'image':self.hologram,
            'squared':self.input_dict['squared'],
            'phase':False,
            'algorithm': 'AS',
            'r': 0.1,
            'wavelength': 3e-10,
            'dxy': .01,
            'scale_factor': 2,
        }
        self.reconstruction, fps = reconstruct(recon_dict)

        self.info_recon.setText(f'Elapsed time for reconstruction: {1/fps}s\n')
        self.reconstruction_ready.emit('reconstruction', self.reconstruction)
