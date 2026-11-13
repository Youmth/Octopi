import threading

from PySide6.QtCore import QThread, Signal

from core.reconstruction import reconstruct


class ReconstructionWorker(QThread):
    """Runs reconstructions off the GUI thread, newest request wins.

    `submit(request)` never blocks. It overwrites any request that has not
    started yet, so dragging a slider can't build a backlog: the worker always
    jumps to the latest parameters and the stale ones are dropped. (A plain
    FIFO queue would keep reconstructing every intermediate slider position
    and fall further and further behind.)

    Signals (delivered on the GUI thread):
        result_ready(image, fps, request)
        failed(message, request)
    `request` is the dict that was submitted, so the receiver knows which
    parameters produced that image.
    """

    result_ready = Signal(object, float, object)
    failed = Signal(str, object)

    def __init__(self, func=reconstruct, parent=None):
        super().__init__(parent)
        self._func = func
        self._cond = threading.Condition()
        self._pending = None
        self._stopping = False

    def submit(self, request: dict):
        with self._cond:
            self._pending = request
            self._cond.notify()

    def run(self):
        while True:
            with self._cond:
                while self._pending is None and not self._stopping:
                    self._cond.wait()
                if self._stopping:
                    return
                request, self._pending = self._pending, None
            try:
                image, fps = self._func(request)
            except Exception as error:  # keep the thread alive for the next request
                self.failed.emit(f"{type(error).__name__}: {error}", request)
            else:
                self.result_ready.emit(image, float(fps), request)

    def stop(self):
        with self._cond:
            self._stopping = True
            self._pending = None
            self._cond.notify()
        self.wait()