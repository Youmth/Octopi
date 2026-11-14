import numpy as np

from core.postprocess import scale_array
from core.propagation import normalize

HOLOGRAM_SPECTRUM = "hologram FFT"
RECONSTRUCTION_SPECTRUM = "reconstruction FFT"


def spectrum(array, scale: str = "log", hide_dc: bool = True, window: bool = True) -> np.ndarray:
    """Magnitude of the centered 2D Fourier transform as a uint8 image.

    scale:   'linear', 'log' or 'sqrt' (see postprocess.SCALES)
    hide_dc: replace the zero-frequency bin by the mean of its 8 neighbours,
             otherwise that single peak crushes the rest of the spectrum
    window:  Hann window before the transform, which removes the cross
             pattern that the image borders would otherwise add
    """
    a = np.asarray(array, dtype=np.float64)
    h, w = a.shape
    if window:
        a = a * np.outer(np.hanning(h), np.hanning(w))
    magnitude = np.abs(np.fft.fftshift(np.fft.fft2(a)))
    if hide_dc and h >= 3 and w >= 3:
        cy, cx = h // 2, w // 2
        block = magnitude[cy - 1:cy + 2, cx - 1:cx + 2]
        magnitude[cy, cx] = (block.sum() - magnitude[cy, cx]) / 8
    return np.uint8(normalize(scale_array(magnitude, scale), 255))


def compute_views(request: dict):
    """Worker function: spectra of the hologram and/or the reconstruction.
    Returns ({image name: array}, 0.0), the shape ReconstructionWorker expects."""
    options = dict(scale=request["fft_scale"], hide_dc=request["hide_dc"], window=request["window"])
    views = {}
    if request["hologram_fft"] and request["hologram"] is not None:
        views[HOLOGRAM_SPECTRUM] = spectrum(request["hologram"], **options)
    if request["reconstruction_fft"] and request["reconstruction"] is not None:
        views[RECONSTRUCTION_SPECTRUM] = spectrum(request["reconstruction"], **options)
    return views, 0.0