from PySide6.QtWidgets import QFileDialog, QLabel, QRadioButton, QButtonGroup, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QComboBox, QCheckBox, QDockWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

from core.io import load_grayscale
from .base import Page
from ui.param_widgets import ParametersPanel, LimitsPanel, ParamSpec
from ui.reconstruction_worker import ReconstructionWorker

import numpy as np


class DLHMStatic(Page):
    title = "Static reconstruction"

    ALGORITHMS = {
        "AS": ("Angular spectrum", ("r", "wavelength", "dxy", "scale_factor")),
        "KR": ("Kreuzer", ("Z", "L", "wavelength", "dxy")),
        "MJ": ("MJ (DLHM model)", ("Z", "L", "wavelength", "dxy", "sensor_width")),
    }

    DEFAULT_ALGORITHM = "AS"

    MODES = {
        'squared' : ('Intensity', True),
        'phase': ('Phase', False),
        'amplitude': ('Amplitude', False)
    }
    DEFAULT_MODE = "phase"

    # All defaults / ranges are in SI units (meters). The panels display them
    # in the unit chosen by the user. Defaults follow the DLHM example in the
    # HoloBio paper (532 nm, 6.9 um pixels, L = 20 mm, z = 6.8 mm).
    PARAMS = {
        "r": ParamSpec("Distance r", 6.8e-3, "length", "Propagation distance",
                       minimum=0.0, maximum=0.05, searchable=True),
        "Z": ParamSpec("Distance Z", 6.8e-3, "length", "Reconstruction distance",
                       minimum=0.0, maximum=0.05, searchable=True),
        "L": ParamSpec("Source distance L", 20e-3, "length", "Point source to detector distance",
                       minimum=1e-3, maximum=0.1, searchable=True),
        "wavelength": ParamSpec("Wavelength", 532e-9, "length", positive=True,
                                minimum=400e-9, maximum=800e-9),
        "dxy": ParamSpec("Pixel pitch dxy", 6.9e-6, "length", positive=True,
                         minimum=1e-6, maximum=20e-6),
        "scale_factor": ParamSpec("Scale factor", 2, positive=True,
                                  minimum=0.5, maximum=10.0),
        "sensor_width": ParamSpec("Sensor width", 5.55e-3, "length", "Width of the sensor (MJ)",
                                  positive=True, minimum=1e-3, maximum=0.02),
    }


    def __init__(self):
        super().__init__()
        # Reconstructions run on this thread; the GUI only submits requests.
        self._worker = ReconstructionWorker()
        self._worker.result_ready.connect(self._on_result)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()
        QApplication.instance().aboutToQuit.connect(self._worker.stop)
        self._live = False
        self._submit_scheduled = True

        self.hologram = None
        self.reconstruction = None
        self.limits = {}  # '<key>_min' / '<key>_max', SI units
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

        self.live_button = QPushButton("Continuous reconstruction")
        self.live_button.setCheckable(True)
        self.live_button.setToolTip("Reconstruct again every time a parameter, mode or algorithm changes")
        self.live_button.toggled.connect(self._set_live)

        # Checkbox panel: lives in a dock, not in this page's layout.
        # Each entry: input_dict key -> (label, default state)
        self.mode_boxes: dict[str, QCheckBox] = {}

        mode_widget = QWidget()
        mode_layout = QVBoxLayout()
        self.mode_group = QButtonGroup(self)
        self.mode_buttons:dict[str,QRadioButton] = {}
        for key, (label, default) in self.MODES.items():
            button = QRadioButton(label)
            self.input_dict[key] = default
            button.toggled.connect(lambda checked, k=key:self.input_dict.__setitem__(k, checked))
            button.toggled.connect(lambda *_: self._request_live())
            self.mode_group.addButton(button)
            self.mode_buttons[key] = button
            mode_layout.addWidget(button)
        mode_layout.addStretch()

        mode_widget.setLayout(mode_layout)

        self.mode_dock = self.add_panel("Mode", mode_widget)

        self.algorithm_box = QComboBox()
        for key, (name, _) in self.ALGORITHMS.items():
            self.algorithm_box.addItem(name, key)
        algorithm_widget = QWidget()
        algorithm_layout = QVBoxLayout(algorithm_widget)
        algorithm_layout.addWidget(self.algorithm_box)
        algorithm_layout.addStretch()
        self.algorithm_dock = self.add_panel("Algorithm", algorithm_widget)

        self.params_panel = ParametersPanel(self.PARAMS, self.input_dict)
        self.params_dock = self.add_panel("Parameters", self.params_panel)

        self.limits_panel = LimitsPanel(self.PARAMS, self.limits)
        self.limits_dock = self.add_panel("Limits", self.limits_panel)
        # One length unit for the whole page
        self.params_panel.unit_changed.connect(self.limits_panel.set_length_unit)
        self.limits_panel.unit_changed.connect(self.params_panel.set_length_unit)
        # The parameter sliders span the limits chosen in the Limits panel
        self.params_panel.follow_limits(self.limits_panel)
        # Any parameter change re-reconstructs when continuous mode is on
        self.params_panel.changed.connect(lambda *_: self._request_live())

        self.algorithm_box.currentIndexChanged.connect(self._on_algorithm_changed)
        self.mode_buttons[self.DEFAULT_MODE].setChecked(True)
        self._on_algorithm_changed()

        self.info = QLabel("No hologram loaded")
        self.info.setWordWrap(True)

        self.info_recon = QLabel("No reconstruction has been performed")
        self.info_recon.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.open_button)
        layout.addWidget(self.info)
        layout.addWidget(self.reconstruct_button)
        layout.addWidget(self.live_button)
        layout.addWidget(self.info_recon)

        layout.addStretch()
    def _on_algorithm_changed(self, *args):
        key = self.algorithm_box.currentData()
        self.input_dict['algorithm'] = key
        self.params_panel.show_only(self.ALGORITHMS[key][1])
        self.limits_panel.show_only(self.ALGORITHMS[key][1])
        self._request_live()
    def _set_mode(self,mode:str):
        self.input_dict['squared'] = mode == "intensity"
        self.input_dict['phase'] = mode=="phase"
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
        self._request_live()


    # ---- reconstruction (runs on the worker thread) -----------------
    def reconstruct_hologram(self):
        """One-shot reconstruction (the button)."""
        if self.hologram is None:
            self.info_recon.setText('Open a hologram first')
            return
        self._submit()

    def _set_live(self, checked: bool):
        self._live = checked
        self.reconstruct_button.setEnabled(not checked)
        if checked:
            if self.hologram is None:
                self.info_recon.setText('Open a hologram first')
            self._request_live()

    def _request_live(self):
        """Ask for a reconstruction if continuous mode is on. Several changes
        in the same event-loop turn (a radio button emits two toggles, a
        unit change touches many rows) collapse into a single request."""
        if not self._live or self.hologram is None or self._submit_scheduled:
            return
        self._submit_scheduled = True
        QTimer.singleShot(0, self._submit)

    def _submit(self):
        self._submit_scheduled = False
        if self.hologram is None:
            return
        request = dict(self.input_dict)  # snapshot: later edits don't affect it
        request['image'] = self.hologram
        self._worker.submit(request)

    def _on_result(self, image, fps, request):
        self.reconstruction = image
        self.reconstruction_ready.emit('reconstruction', image)

        name, parameters = self.ALGORITHMS[request['algorithm']]
        text = ''
        for parameter in parameters:
            text += f"{parameter.upper()} : {self.params_panel.describe(parameter, request[parameter])}\n"
        timing = f"{1 / fps:.3f} s ({fps:.1f} fps)" if fps > 0 else "n/a"
        self.info_recon.setText(f"{name}\n{text}\nReconstruction time: {timing}")

    def _on_failed(self, message, request):
        self.info_recon.setText(f"Reconstruction failed:\n{message}")