from .dlhm_realtime import DLHMRealTime
from .dlhm_static import DLHMStatic
from .dhm import DHMPage
from .optical_imaging import OpticalImagingPage
from .fiber import FiberPage

# Tabs are the fields of study, subtabs are the techniques.
PAGES = {
    "DLHM": [DLHMRealTime, DLHMStatic],
    "DHM": [DHMPage],
    "Optical Imaging": [OpticalImagingPage],
    "Fiber": [FiberPage],
}

GLUE_GAP = 10