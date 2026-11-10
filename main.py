


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication
    import cupy as cp
    import sys

    from ui.MainWindow import MainWindow

    print(sys.version)
    print(cp.cuda.runtime.getDeviceCount())
    print(cp.fft.fft2(cp.random.rand(1024,1024)).shape)
    print('Hello motherfuckersss')
    print('Initiating application...')

    app = QApplication([])

    window = MainWindow()
    window.show()

    app.exec()
