Feature list for the static side



Analysis

Autofocus. ROI-based, with variance, acutance and Tenengrad metrics, a focus-curve plot, and a z-scan sweep mode.
ROI tools as canvas items: lines, rectangles and circles, with a live profile plot.
Measurements: distances in µm, phase thickness from refractive indices, and phase unwrapping.
Segmentation and particle analysis: Otsu, manual and adaptive thresholds, particle counts and areas, histograms.
Speckle toolkit: speckle contrast and filters.
Export: images plus a JSON file with all parameters, so every result can be reproduced.

Validation, running alongside everything

Regression tests using your validation folder, comparing CuPy against NumPy and against the known results. When we get there, tell me how the folder is organized.

Última acción 11/11:
Mucho se ha avanzado, incluí (con ayuda de Claude) Una arquitectura para Octopi! mejor estructurada. Hay tres carpetas principales: core, gpu, ui. En core estan todas las funciones relacionadas a edición de imagenes y algoritmos de simulación, así como entrada y salida de datos, básicamente todo el backende. En gpu van a estar las funciones de reconstrucción que se puedan acelerar con GPU, y todo lo relacionado a io de GPU. En ui están todas las cosas de PySide6. 

Específicamente en ui, hay dos archivos correspondientes a los dos elementos principales de la aplicación, el primero es el workspace, que es un canvas gráfico donde puedes poner imágenes, widgets flotantes (como sliders, menus, botones, etc), información en forma de texto, etc. El segundo elemento es la ventana principal (MainWindow) y es donde están los diferentes menus (en forma de tabs) y las páginas que contendran las diferentes funcionalidades de la aplicación. 

Dentro de ui hay un directorio llamado pages, en él están todas las páginas, cada una con su funcionalidad y elementos propios. Por ahora, la página dlhm_static es la que estoy procurando avanzar, las demás están con un placeholder. Las páginas se basan en una clase base que incluye un nombre, para ser representado en la etiqueta de la pestaña a la que está asociada, y por ahora tengo implementadas dos señales en esta clase, para poder acceder a las imágenes y enviarlas al viewport, de esta forma se comunican los dos.