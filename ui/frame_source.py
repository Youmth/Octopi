import sys
import threading
import time

from PySide6.QtCore import QThread, Signal


class CameraSource(QThread):
    """Grabs frames with OpenCV on its own thread: a camera index (int) or a
    video file (str, played at its own frame rate and looped).

    Same philosophy as ReconstructionWorker: no backlog. The thread keeps only
    the NEWEST frame and emits `frame_ready` (no payload) when there is one the
    GUI hasn't taken yet; the GUI calls `take()` to fetch it. A slow GUI makes
    the source skip frames instead of queueing them.
    """

    frame_ready = Signal()
    failed = Signal(str)

    def __init__(self, source=0, parent=None):
        super().__init__(parent)
        self._source = source
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._latest = None
        self._signalled = False

    def take(self):
        """Newest grayscale frame (uint8) or None. Call from the GUI thread."""
        with self._lock:
            frame, self._latest, self._signalled = self._latest, None, False
        return frame

    def run(self):
        import cv2  # pip install opencv-python

        is_file = isinstance(self._source, str)
        if is_file or sys.platform != "win32":
            cap = cv2.VideoCapture(self._source)
        else:
            cap = cv2.VideoCapture(self._source, cv2.CAP_DSHOW)  # faster start-up on Windows
        if not cap.isOpened():
            self.failed.emit(f"Could not open {'video' if is_file else 'camera'} {self._source!r}")
            return

        period = 1.0 / (cap.get(cv2.CAP_PROP_FPS) or 30.0)
        rewound = False
        while not self._stop.is_set():
            started = time.perf_counter()
            ok, frame = cap.read()
            if not ok:
                if is_file and not rewound:  # loop the video once per failure
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    rewound = True
                    continue
                self.failed.emit("The source stopped delivering frames")
                break
            rewound = False
            if frame.ndim == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            with self._lock:
                self._latest = frame
                notify = not self._signalled
                self._signalled = True
            if notify:
                self.frame_ready.emit()

            if is_file:  # a camera paces itself; a file would run at full speed
                time.sleep(max(0.0, period - (time.perf_counter() - started)))
        cap.release()

    def stop(self):
        self._stop.set()
        self.wait()