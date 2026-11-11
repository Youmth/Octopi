import numpy as np
from core.propagation import normalize
from skimage import exposure, filters


def gamma_filter(arr, gamma):
    return np.uint8(np.clip(arr + gamma * 255, 0, 255))

def contrast_filter(arr, contrast):
    return np.uint8(np.clip(arr * contrast, 0, 255))

def adaptative_eq_filter(arr, _):
    arr = exposure.equalize_adapthist(normalize(arr, 1), clip_limit=DEFAULT_CLIP_LIMIT)
    return np.uint8(arr * 255)  # Convertir de 0-1 a 0-255

def highpass_filter(arr, freq):
    arr = filters.butterworth(normalize(arr, 1), freq, high_pass=True)
    return np.uint8(arr*255)

def lowpass_filter(arr, freq):
    arr = filters.butterworth(normalize(arr, 1), freq, high_pass=False)
    return np.uint8(arr*255)