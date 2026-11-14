from core.reconstruction import reconstruct
from ui.param_widgets import ParamSpec
from ui.pages.reconstruction_page import ReconstructionPage


class DLHMPage(ReconstructionPage):
    """What DLHM reconstructs. Static and real-time DLHM share all of it, so
    the two pages differ only in where the hologram comes from."""

    ALGORITHMS = {
        "AS": ("Angular spectrum", ("r", "wavelength", "dxy", "scale_factor")),
        "KR": ("Kreuzer", ("Z", "L", "wavelength", "dxy")),
        "MJ": ("MJ (DLHM model)", ("Z", "L", "wavelength", "dxy", "sensor_width")),
    }
    DEFAULT_ALGORITHM = "AS"

    MODES = {  # key -> (label, starts checked); the checked one must be DEFAULT_MODE
        "squared": ("Intensity", False),
        "phase": ("Phase", True),
        "amplitude": ("Amplitude", False),
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
    reconstruct_func = staticmethod(reconstruct)  # the page's reconstruction function