from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QApplication,
)

from ui.frame_source import CameraSource
from ui.pages.dlhm_base import DLHMPage


class DLHMRealTime(DLHMPage):
    """DLHM on live frames from a camera or a video file. The reconstruction
    runs continuously while the source is on; the camera keeps delivering
    frames even if reconstruction is slower (the worker keeps only the newest)."""
    title = "Real time reconstruction"

    def __init__(self):
        super().__init__()
        self._source = None
        self._source_arg = None     # what the running source was opened with
        self._resume_source = None  # remembered while the page is hidden
        QApplication.instance().aboutToQuit.connect(self._stop_source)

        self.camera_index = QSpinBox()
        self.camera_index.setRange(0, 9)
        self.camera_button = QPushButton("Start camera")
        self.camera_button.setCheckable(True)
        self.camera_button.toggled.connect(self._toggle_camera)
        self.video_button = QPushButton("Play video file...")
        self.video_button.clicked.connect(self._open_video)
        self.info = QLabel("No source running")
        self.info.setWordWrap(True)
        self.info_recon.setText("")

        row = QHBoxLayout()
        row.addWidget(QLabel("Camera"))
        row.addWidget(self.camera_index)
        row.addWidget(self.camera_button, 1)

        layout = QVBoxLayout(self)
        layout.addLayout(row)
        layout.addWidget(self.video_button)
        layout.addWidget(self.info)
        layout.addWidget(self.common_widget)  # reference, recording, result info
        layout.addStretch()

    # ---- source control ----------------------------------------------------
    def _toggle_camera(self, checked: bool):
        if checked:
            self._start_source(self.camera_index.value())
        else:
            self._stop_source()

    def _open_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Play video", "", "Videos (*.avi *.mp4 *.mov *.mkv)")
        if path:
            self._start_source(path)

    def _start_source(self, source):
        self._stop_source()
        self._source = CameraSource(source)
        self._source_arg = source
        self._source.frame_ready.connect(self._on_frame)
        self._source.failed.connect(self._on_source_failed)
        self._source.start()
        self.live_button.setChecked(True)  # a running source reconstructs continuously
        self.info.setText(f"Running: {source}")
        self._set_camera_button(isinstance(source, int))

    def _stop_source(self):
        if self._source is None:
            return
        source, self._source = self._source, None
        source.stop()
        self.info.setText("No source running")
        self._set_camera_button(False)

    def _set_camera_button(self, checked: bool):
        self.camera_button.blockSignals(True)
        self.camera_button.setChecked(checked)
        self.camera_button.setText("Stop camera" if checked else "Start camera")
        self.camera_button.blockSignals(False)

    def _on_frame(self):
        if self._source is None:
            return
        frame = self._source.take()
        if frame is not None:
            self.set_hologram(frame)

    def _on_hologram_removed(self):
        """The user deleted the hologram image: let go of the camera / video."""
        self._stop_source()

    def _on_source_failed(self, message: str):
        self._stop_source()
        self.info.setText(message)

    # ---- lifecycle: don't hold the camera while the tab is hidden -----------
    def on_hide(self):
        super().on_hide()
        self._resume_source = self._source_arg if self._source is not None else None
        self._stop_source()

    def on_show(self):
        super().on_show()
        if self._resume_source is not None:
            self._start_source(self._resume_source)
            self._resume_source = None