import numpy as np

from core.propagation import normalize

# Neutral values: apply_filters returns its input untouched when all of them
# are at these values, so an idle filter panel costs nothing.
FILTER_DEFAULTS = {"highpass": 0.0, "lowpass": 0.5, "contrast": 1.0, "brightness": 0.0}


def butterworth(arr: np.ndarray, cutoff: float, high_pass: bool, order: int = 2) -> np.ndarray:
    """Butterworth filter in the Fourier domain. `cutoff` is in cycles/pixel
    (0.5 = Nyquist). Plain numpy, so scikit-image is not needed."""
    rows, cols = arr.shape
    f = np.hypot(np.fft.fftfreq(cols)[None, :], np.fft.fftfreq(rows)[:, None])
    if high_pass:
        with np.errstate(divide="ignore"):
            gain = 1.0 / (1.0 + (cutoff / f) ** (2 * order))  # f = 0 -> gain 0
    else:
        gain = 1.0 / (1.0 + (f / cutoff) ** (2 * order))
    return np.fft.ifft2(np.fft.fft2(arr) * gain).real


def apply_filters(arr: np.ndarray, params: dict) -> np.ndarray:
    """High-pass, low-pass, then contrast and brightness on a 0-255 image.
    Returns the input unchanged if every filter is neutral, else a uint8 image."""
    highpass = params.get("highpass", FILTER_DEFAULTS["highpass"])
    lowpass = params.get("lowpass", FILTER_DEFAULTS["lowpass"])
    contrast = params.get("contrast", FILTER_DEFAULTS["contrast"])
    brightness = params.get("brightness", FILTER_DEFAULTS["brightness"])

    filter_freq = highpass > 0 or lowpass < 0.5
    if not filter_freq and contrast == 1.0 and brightness == 0.0:
        return arr

    out = arr.astype(np.float64)
    if highpass > 0:
        out = butterworth(out, highpass, high_pass=True)
    if lowpass < 0.5:
        out = butterworth(out, lowpass, high_pass=False)
    if filter_freq:
        out = normalize(out, 255)  # frequency filters change the range
    out = out * contrast + brightness * 255
    return np.uint8(np.clip(out, 0, 255))


SCALES = {"linear": "Linear", "log": "Logarithmic", "sqrt": "Square root"}


def scale_array(arr: np.ndarray, kind: str) -> np.ndarray:
    """Non-linear intensity scaling for display. 'linear' returns the input
    untouched; 'log' and 'sqrt' return a 0-255 float image (the minimum is
    shifted to 0 first, so phase images with negative values work too)."""
    if kind == "linear":
        return arr
    a = arr.astype(np.float64)
    a = a - a.min()
    a = np.log1p(a) if kind == "log" else np.sqrt(a)
    return normalize(a, 255)