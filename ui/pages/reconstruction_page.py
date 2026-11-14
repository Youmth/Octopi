from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QComboBox, QFileDialog, QGroupBox, QLabel,
    QMessageBox, QPushButton, QRadioButton, QVBoxLayout, QWidget,
)

from core.io import load_grayscale
from core.postprocess import SCALES
from core.reconstruction import reconstruct
from core.views import HOLOGRAM_SPECTRUM, RECONSTRUCTION_SPECTRUM, compute_views
from ui.param_widgets import FiltersPanel, LimitsPanel, ParametersPanel, ParamSpec
from ui.pages.base import Page
from ui.reconstruction_worker import ReconstructionWorker


class ReconstructionPage(Page):
    """Everything that is the same on every page that reconstructs holograms:
    mode / algorithm / parameters / limits / filters panels, the background
    workers, continuous reconstruction, reference hologram and recording.

    A concrete page only declares WHAT it reconstructs (ALGORITHMS, PARAMS,
    MODES, `reconstruct_func`) and WHERE hologram frames come from (a file, a
    camera...): it lays out its own buttons and calls `set_hologram(frame)`.
    """

    ALGORITHMS: dict = {}   # key -> (name, (parameter keys it uses))
    DEFAULT_ALGORITHM: str = ""
    MODES: dict = {}        # input_dict key -> (label, default checked)
    DEFAULT_MODE: str = ""
    PARAMS: dict = {}       # key -> ParamSpec (SI units)
    reconstruct_func = staticmethod(reconstruct)
    RECORD_FPS = 15.0

    FILTER_PARAMS = {
        "highpass": ParamSpec("High-pass cutoff", 0.0, tooltip="Cycles/pixel. 0 = off",
                              minimum=0.0, maximum=0.25),
        "lowpass": ParamSpec("Low-pass cutoff", 0.5, tooltip="Cycles/pixel. 0.5 = off",
                             positive=True, minimum=0.01, maximum=0.5),
        "contrast": ParamSpec("Contrast", 1.0, tooltip="Multiplier. 1 = off",
                              positive=True, minimum=0.1, maximum=5.0),
        "brightness": ParamSpec("Brightness", 0.0, tooltip="Offset as a fraction of the range. 0 = off",
                                minimum=-0.5, maximum=0.5),
    }

    def __init__(self):
        super().__init__()
        # Reconstructions run on this thread; the GUI only submits requests.
        self._worker = ReconstructionWorker(self.reconstruct_func)
        self._worker.result_ready.connect(self._on_result)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()
        # Spectra get their own thread so a big FFT never delays a reconstruction
        self._view_worker = ReconstructionWorker(compute_views)
        self._view_worker.result_ready.connect(self._on_views_ready)
        self._view_worker.failed.connect(self._on_failed)
        self._view_worker.start()
        QApplication.instance().aboutToQuit.connect(self._shutdown)

        self._live = False
        self._submit_scheduled = False
        self._recon_visible = True  # False after the user deletes the reconstruction image
        self._recorder = None

        self.hologram = None
        self.reference = None
        self.reconstruction = None
        self.limits = {}   # '<key>_min' / '<key>_max', SI units
        self.filters = {}  # display filters
        self.views = {     # Fourier views (computed on the view worker)
            'hologram_fft': False, 'reconstruction_fft': False,
            'fft_scale': 'log', 'hide_dc': True, 'window': True,
        }
        self.input_dict = {'image': None, 'algorithm': None, 'scale': 'linear'}

        self._build_mode_panel()
        self._build_algorithm_panel()
        self._build_parameter_panels()
        self._build_common_widget()

        self.algorithm_box.currentIndexChanged.connect(self._on_algorithm_changed)
        self.mode_buttons[self.DEFAULT_MODE].setChecked(True)
        self._on_algorithm_changed()

    # ---- panels ----------------------------------------------------------
    def _radio_group(self, layout, options: dict, default: str, on_select):
        """Radio buttons for {key: label}, one exclusive group; calls on_select(key)."""
        group = QButtonGroup(self)
        buttons = {}
        for key, label in options.items():
            button = QRadioButton(label)
            button.setChecked(key == default)
            button.toggled.connect(lambda checked, k=key: checked and on_select(k))
            group.addButton(button)
            layout.addWidget(button)
            buttons[key] = button
        return group, buttons

    def _build_mode_panel(self):
        """Everything about WHAT is shown, in two groups: the reconstruction
        (quantity + scaling) and the Fourier spectra."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        recon_box = QGroupBox("Reconstruction")
        recon_layout = QVBoxLayout(recon_box)
        self.mode_group = QButtonGroup(self)
        self.mode_buttons: dict[str, QRadioButton] = {}
        for key, (label, _) in self.MODES.items():
            button = QRadioButton(label)
            self.input_dict[key] = key == self.DEFAULT_MODE  # only the default mode starts on
            button.toggled.connect(lambda checked, k=key: self.input_dict.__setitem__(k, checked))
            button.toggled.connect(lambda *_: self._request_live())
            self.mode_group.addButton(button)
            self.mode_buttons[key] = button
            recon_layout.addWidget(button)
        recon_layout.addWidget(QLabel("Scale"))
        self.scale_group, self.scale_buttons = self._radio_group(
            recon_layout, SCALES, 'linear', self._set_scale)
        layout.addWidget(recon_box)

        fft_box = QGroupBox("Fourier transform")
        fft_layout = QVBoxLayout(fft_box)
        self.hologram_fft_box = QCheckBox("Hologram spectrum")
        self.reconstruction_fft_box = QCheckBox("Reconstruction spectrum")
        self.hologram_fft_box.setToolTip("Adds an image with the Fourier spectrum of the hologram")
        self.reconstruction_fft_box.setToolTip("Adds an image with the Fourier spectrum of the displayed reconstruction")
        self.hologram_fft_box.toggled.connect(lambda on: self._set_view('hologram_fft', on))
        self.reconstruction_fft_box.toggled.connect(lambda on: self._set_view('reconstruction_fft', on))
        fft_layout.addWidget(self.hologram_fft_box)
        fft_layout.addWidget(self.reconstruction_fft_box)
        fft_layout.addWidget(QLabel("Spectrum scale"))
        self.fft_scale_group, self.fft_scale_buttons = self._radio_group(
            fft_layout, SCALES, self.views['fft_scale'], lambda k: self._set_view('fft_scale', k))
        self.hide_dc_box = QCheckBox("Hide DC peak")
        self.hide_dc_box.setToolTip("Replace the zero-frequency bin by its neighbours' mean")
        self.hide_dc_box.setChecked(self.views['hide_dc'])
        self.hide_dc_box.toggled.connect(lambda on: self._set_view('hide_dc', on))
        self.window_box = QCheckBox("Hann window")
        self.window_box.setToolTip("Fade the borders before the transform (removes the cross artifact)")
        self.window_box.setChecked(self.views['window'])
        self.window_box.toggled.connect(lambda on: self._set_view('window', on))
        fft_layout.addWidget(self.hide_dc_box)
        fft_layout.addWidget(self.window_box)
        layout.addWidget(fft_box)

        layout.addStretch()
        self.mode_dock = self.add_panel("Mode", widget)

    def _set_scale(self, key: str):
        self.input_dict['scale'] = key
        self._request_live()

    def _build_algorithm_panel(self):
        self.algorithm_box = QComboBox()
        for key, (name, _) in self.ALGORITHMS.items():
            self.algorithm_box.addItem(name, key)
        self.algorithm_box.setCurrentIndex(self.algorithm_box.findData(self.DEFAULT_ALGORITHM))
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(self.algorithm_box)
        layout.addStretch()
        self.algorithm_dock = self.add_panel("Algorithm", widget)

    def _build_parameter_panels(self):
        self.params_panel = ParametersPanel(self.PARAMS, self.input_dict)
        self.params_dock = self.add_panel("Parameters", self.params_panel)

        self.limits_panel = LimitsPanel(self.PARAMS, self.limits)
        self.limits_dock = self.add_panel("Limits", self.limits_panel)
        # One length unit for the whole page
        self.params_panel.unit_changed.connect(self.limits_panel.set_length_unit)
        self.limits_panel.unit_changed.connect(self.params_panel.set_length_unit)
        # The parameter sliders span the limits chosen in the Limits panel
        self.params_panel.follow_limits(self.limits_panel)
        self.params_panel.changed.connect(lambda *_: self._request_live())

        self.filters_panel = FiltersPanel(self.FILTER_PARAMS, self.filters)
        self.filters_dock = self.add_panel("Filters", self.filters_panel)
        self.filters_panel.changed.connect(lambda *_: self._request_live())

    def _build_common_widget(self):
        """Live toggle, reference, recording and the result info. Pages put
        `self.common_widget` wherever they like in their own layout."""
        self.live_button = QPushButton("Continuous reconstruction")
        self.live_button.setCheckable(True)
        self.live_button.setToolTip("Reconstruct again every time a parameter, mode, algorithm or frame changes")
        self.live_button.toggled.connect(self._set_live)

        self.reference_button = QPushButton("Load reference...")
        self.reference_button.setToolTip("A hologram taken without the sample, subtracted from the hologram")
        self.reference_button.clicked.connect(self.load_reference)
        self.reference_box = QCheckBox("Subtract reference")
        self.reference_box.setEnabled(False)
        self.reference_box.toggled.connect(lambda *_: self._request_live())

        self.record_button = QPushButton("Start recording")
        self.record_button.setCheckable(True)
        self.record_button.setToolTip("Save hologram and reconstruction videos with their parameters")
        self.record_button.toggled.connect(self._toggle_recording)
        self.record_label = QLabel("")
        self.info_recon = QLabel("")
        self.info_recon.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.common_widget = QWidget()
        layout = QVBoxLayout(self.common_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        for widget in (self.live_button, self.reference_button, self.reference_box,
                       self.record_button, self.record_label, self.info_recon):
            layout.addWidget(widget)

    # ---- frames in -------------------------------------------------------
    def set_hologram(self, array):
        """Every frame source (file, camera...) ends up here."""
        self.hologram = array
        self.image_ready.emit("hologram", array)
        self._request_views()
        self._request_live()

    def load_reference(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open reference hologram", "", "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)")
        if not path:
            return
        self.reference = load_grayscale(path)
        self.reference_button.setText(f"Reference: {Path(path).name}")
        self.reference_box.setEnabled(True)
        self.reference_box.setChecked(True)

    # ---- Fourier views (own worker thread) ----------------------------------
    def _set_view(self, key: str, value):
        self.views[key] = value
        if key == 'hologram_fft' and not value:
            self.remove_image.emit(HOLOGRAM_SPECTRUM)
        elif key == 'reconstruction_fft' and not value:
            self.remove_image.emit(RECONSTRUCTION_SPECTRUM)
        self._request_views()

    def _request_views(self):
        if not (self.views['hologram_fft'] or self.views['reconstruction_fft']):
            return
        request = {**self.views, 'hologram': self.hologram, 'reconstruction': self.reconstruction}
        self._view_worker.submit(request)

    def _on_views_ready(self, views, _fps, _request):
        wanted = {HOLOGRAM_SPECTRUM: self.views['hologram_fft'],
                  RECONSTRUCTION_SPECTRUM: self.views['reconstruction_fft']}
        for name, array in views.items():
            if wanted.get(name):  # the box may have been unchecked meanwhile
                self.image_ready.emit(name, array)

    # ---- reconstruction (runs on the worker thread) ------------------------
    def reconstruct_hologram(self):
        """One-shot reconstruction."""
        if self.hologram is None:
            self.info_recon.setText("No hologram yet")
            return
        self._submit()

    def _set_live(self, checked: bool):
        self._live = checked
        self._on_live_changed(checked)
        if checked:
            if self.hologram is None:
                self.info_recon.setText("No hologram yet")
            self._request_live()

    def _on_live_changed(self, checked: bool):
        """Hook: pages update their own widgets."""

    def _request_live(self):
        """Ask for a reconstruction if continuous mode is on. Several changes in
        the same event-loop turn (a radio button emits two toggles, a unit
        change touches many rows) collapse into a single request."""
        if not self._live or self.hologram is None or self._submit_scheduled:
            return
        self._submit_scheduled = True
        QTimer.singleShot(0, self._submit)

    def _submit(self):
        self._submit_scheduled = False
        if self.hologram is None:
            return
        self._recon_visible = True
        # Snapshot: later edits don't affect a request already queued
        request = {**self.input_dict, **self.filters}
        request['image'] = self.hologram
        request['reference'] = self.reference if self.reference_box.isChecked() else None
        self._worker.submit(request)

    def _on_algorithm_changed(self):
        key = self.algorithm_box.currentData()
        self.input_dict['algorithm'] = key
        self.params_panel.show_only(self.ALGORITHMS[key][1])
        self.limits_panel.show_only(self.ALGORITHMS[key][1])
        self._request_live()

    def _on_result(self, image, fps, request):
        if not self._recon_visible:  # the user deleted the image while this one was computing
            return
        self.reconstruction = image
        self.reconstruction_ready.emit('reconstruction', image)
        self._request_views()

        name, parameters = self.ALGORITHMS[request['algorithm']]
        text = ''.join(f"{p.upper()} : {self.params_panel.describe(p, request[p])}\n" for p in parameters)
        timing = f"{1 / fps:.3f} s ({fps:.1f} fps)" if fps > 0 else "n/a"
        self.info_recon.setText(f"{name}\n{text}\nReconstruction time: {timing}")

        if self._recorder is not None:
            try:
                frames = self._recorder.write(request['image'], image, request)
            except Exception as error:
                self._recording_failed(error)
            else:
                self.record_label.setText(f"Recording: {frames} frames")

    def _on_failed(self, message, request):
        self.info_recon.setText(f"Reconstruction failed:\n{message}")

    # ---- the user deleted an image from the workspace ----------------------
    def on_image_removed(self, name: str):
        if name == "hologram":
            self.hologram = None
            self._stop_recording()
            self.remove_image.emit(HOLOGRAM_SPECTRUM)  # its source is gone
            self._on_hologram_removed()
        elif name == "reconstruction":
            self.reconstruction = None
            self._recon_visible = False  # drop a result that is still computing
            self.live_button.setChecked(False)
            self.remove_image.emit(RECONSTRUCTION_SPECTRUM)
        elif name == HOLOGRAM_SPECTRUM:
            self.hologram_fft_box.setChecked(False)
        elif name == RECONSTRUCTION_SPECTRUM:
            self.reconstruction_fft_box.setChecked(False)

    def _on_hologram_removed(self):
        """Hook: pages stop their source and offer to load another one."""

    # ---- recording --------------------------------------------------------
    def _toggle_recording(self, checked: bool):
        if not checked:
            self._stop_recording()
            return
        folder = QFileDialog.getExistingDirectory(self, "Folder for the recording")
        if not folder:
            self.record_button.setChecked(False)
            return
        from core.recording import Recorder
        keys = ['algorithm', *self.MODES, 'scale', *self.PARAMS, *self.FILTER_PARAMS]
        try:
            self._recorder = Recorder(folder, self.RECORD_FPS, keys)
        except Exception as error:  # e.g. opencv missing
            self.record_button.setChecked(False)
            QMessageBox.warning(self, "Recording failed", str(error))
            return
        self.record_button.setText("Stop recording")
        self.record_label.setText("Recording: 0 frames")
        self._request_live()  # reconstruct at once: frames are written as results arrive
        if not self._live:
            self.reconstruct_hologram()

    def _stop_recording(self):
        if self._recorder is None:
            return
        recorder, self._recorder = self._recorder, None
        recorder.close()
        self.record_button.blockSignals(True)
        self.record_button.setChecked(False)
        self.record_button.blockSignals(False)
        self.record_button.setText("Start recording")
        self.record_label.setText(f"Saved {recorder.frames} frames to {recorder.folder}")

    def _recording_failed(self, error):
        self._stop_recording()
        QMessageBox.warning(self, "Recording stopped", str(error))

    # ---- lifecycle ---------------------------------------------------------
    def on_hide(self):
        super().on_hide()
        self._stop_recording()

    def _shutdown(self):
        self._stop_recording()
        self._worker.stop()
        self._view_worker.stop()