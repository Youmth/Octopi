Feature list for the static side

Core loop

Reconstruction image glued to the hologram. A second canvas item attached to the right edge of the imported hologram. It moves, rotates and scales together with it, so the pair always stays side by side. Labeled, with the same pixel grid. Later you can detach and re-attach it.
Parameter panel. Wavelength, pixel pitch (x and y), L, z, r and magnification (L/Z), with units. It keeps the old app’s relationships between them (r = L − Z, the “fix r” option, editable limits).
Angular spectrum reconstruction in core/propagation.py, written with xp=np. It recomputes when a parameter changes and has a debounce so dragging a slider doesn’t queue stale work.
Output mode: amplitude, intensity or phase.
Distance controls. The slider and numeric entry stay in sync, and the slider range is editable.
Second algorithm. Kreuzer/KHDI, with a method selector. The spherical-illumination modified angular spectrum (MAS) can follow later.
Reference hologram. Load a sample-free reference and subtract it from the hologram before reconstruction.
GPU backend. A CuPy switch with CPU fallback, plus a timing readout to compare both.

Viewing

View modes: hologram, Fourier spectrum, amplitude and phase, with colormaps.
Display versus processing. Display adjustments (range, gamma, colormap) never change the data. Processing filters (contrast, CLAHE, Butterworth high and low pass) are separate and can target the hologram or the reconstruction.
Pixel inspector. Cursor position in pixels and µm, the value under the cursor, and a scale bar.
Floating panels. The controls move from the dock to overlays on the canvas.

Analysis

Autofocus. ROI-based, with variance, acutance and Tenengrad metrics, a focus-curve plot, and a z-scan sweep mode.
ROI tools as canvas items: lines, rectangles and circles, with a live profile plot.
Measurements: distances in µm, phase thickness from refractive indices, and phase unwrapping.
Segmentation and particle analysis: Otsu, manual and adaptive thresholds, particle counts and areas, histograms.
Speckle toolkit: speckle contrast and filters.
Export: images plus a JSON file with all parameters, so every result can be reproduced.

Validation, running alongside everything

Regression tests using your validation folder, comparing CuPy against NumPy and against the known results. When we get there, tell me how the folder is organized.