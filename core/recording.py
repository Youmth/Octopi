import csv
import time
from datetime import datetime
from pathlib import Path

import numpy as np

from core.propagation import normalize


def _to_uint8(array: np.ndarray) -> np.ndarray:
    a = np.asarray(array)
    return a if a.dtype == np.uint8 else np.uint8(normalize(a, 255))


class Recorder:
    """Records paired frames (raw hologram + its reconstruction) into a new
    folder: hologram.avi, reconstruction.avi (MJPG, grayscale) and frames.csv
    with the parameters that produced every frame, so a recording can be
    reproduced. One call to `write` = one frame in each video."""

    def __init__(self, parent_folder, fps: float = 15.0, keys=()):
        import cv2  # pip install opencv-python
        self._cv2 = cv2
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.folder = Path(parent_folder) / f"recording_{stamp}"
        self.folder.mkdir(parents=True)
        self.fps = fps
        self.keys = list(keys)
        self.frames = 0
        self._writers = {}  # name -> (VideoWriter, (h, w))
        self._csv_file = open(self.folder / "frames.csv", "w", newline="", encoding="utf-8")
        self._csv = csv.writer(self._csv_file)
        self._csv.writerow(["frame", "time_s", *self.keys])
        self._t0 = time.perf_counter()

    def _writer(self, name: str, frame: np.ndarray):
        if name not in self._writers:
            h, w = frame.shape
            fourcc = self._cv2.VideoWriter_fourcc(*"MJPG")
            writer = self._cv2.VideoWriter(str(self.folder / f"{name}.avi"), fourcc, self.fps, (w, h), False)
            if not writer.isOpened():
                raise RuntimeError(f"Could not open a video writer for {name}.avi")
            self._writers[name] = (writer, (h, w))
        writer, shape = self._writers[name]
        if frame.shape != shape:
            raise ValueError(f"Frame size changed during recording ({shape} -> {frame.shape})")
        return writer

    def write(self, hologram, reconstruction, request: dict) -> int:
        frames = {"hologram": _to_uint8(hologram), "reconstruction": _to_uint8(reconstruction)}
        for name, frame in frames.items():
            self._writer(name, frame).write(frame)
        self._csv.writerow([self.frames, f"{time.perf_counter() - self._t0:.4f}",
                            *(request.get(key) for key in self.keys)])
        self.frames += 1
        return self.frames

    def close(self):
        for writer, _ in self._writers.values():
            writer.release()
        self._writers.clear()
        self._csv_file.close()