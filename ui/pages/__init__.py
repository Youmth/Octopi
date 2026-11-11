from .dlhm_realtime import DLHMRealTime
from .dlhm_static import DLHMStatic
from .dlhm_contrast import DLHMContrast
from .dhm import DHMPage
from .optical_imaging import OpticalImagingPage
from .fiber import FiberPage

# Tabs are the fields of study, subtabs are the techniques.
PAGES = {
    "DLHM": [DLHMRealTime, DLHMStatic, DLHMContrast],
    "DHM": [DHMPage],
    "Optical Imaging": [OpticalImagingPage],
    "Fiber": [FiberPage],
}
