import numpy as np


def roi_mask(shape, spec) -> np.ndarray:
    """Boolean mask of a region in pixel coordinates (pixel i spans [i, i+1]).

    spec: ("rect", x0, y0, x1, y1)  or  ("circle", cx, cy, radius)
    A pixel is inside when its center is.
    """
    h, w = shape
    xs = np.arange(w) + 0.5          # broadcasting instead of meshgrid: no
    ys = np.arange(h)[:, None] + 0.5  # big temporary arrays on large images
    if spec[0] == "rect":
        _, x0, y0, x1, y1 = spec
        return (xs >= x0) & (xs <= x1) & (ys >= y0) & (ys <= y1)
    _, cx, cy, radius = spec
    return (xs - cx) ** 2 + (ys - cy) ** 2 <= radius ** 2


def apply_roi(array, spec) -> np.ndarray:
    """Same-size copy of `array` with everything outside the region set to 0."""
    a = np.asarray(array)
    return np.where(roi_mask(a.shape, spec), a, 0).astype(a.dtype)