import numpy as np
import cv2 as cv  # pip install opencv-python


def dlhm(sample, dx_in, L, z, W_c, dx_out, wavelength, x0=0, y0=0):
    """
    Digital Lensless Holography Model (DLHM), ported from the 'MJ' algorithm
    of the avanzado-2 project.

    Args:
    sample: 2D array
        Input complex field (wavefront).
    dx_in: float
        Pixel size of the input (0 skips the resampling stage).
    z: float
        Distance from the point source to the hologram plane.
    L: float
        Distance from the point source to the sample plane.
    W_c: float
        Width of the sensor.
    dx_out: float
        Pixel size at the sensor.
    wavelength: float
        Wavelength of the light.
    x0, y0: float, optional
        Offsets (in pixels) to adjust the center of the cropped sample.

    All lengths must share one unit (the app always passes meters).
    """

    N, M = sample.shape

    # The discretization on the camera is the same as the input's
    P = M
    Q = N

    Mag = L / z                 # magnification
    W_s = W_c / Mag             # field of view that will be propagated

    if dx_in != 0:
        # Resample so the sample's pixel matches the desired magnification
        res_d = dx_in * Mag / dx_out
        sample = resize(sample, int(M / res_d), int(N / res_d))
        N_s, M_s = sample.shape
        W_sample = N_s * dx_out / Mag

        if W_sample > W_s:
            # Provided field of view is larger than what the system captures:
            # keep only the illuminated portion.
            sample = sample[N_s // 2 - N // 2:N_s // 2 + N // 2,
                            M_s // 2 - M // 2:M_s // 2 + M // 2]
        else:
            sample = resize(sample, P, Q)

        # Crop according to magnification and offsets
        start_x = int(N / 2 - N / (Mag * 2) + x0)
        end_x = int(N / 2 + N / (Mag * 2) + x0)
        start_y = int(M / 2 - M / (Mag * 2) + y0)
        end_y = int(M / 2 + M / (Mag * 2) + y0)
        sample = sample[start_x:end_x, start_y:end_y]

        sample = resize(sample, P, Q)

    k = 2 * np.pi / wavelength

    # Spatial frequency coordinates at the sample's plane
    dfx = Mag / (dx_out * M)
    dfy = Mag / (dx_out * N)
    fx, fy = np.meshgrid(np.arange(-M / 2 * dfx, M / 2 * dfx, dfx),
                         np.arange(-N / 2 * dfy, N / 2 * dfy, dfy))

    # Angular spectrum propagation kernel
    E = np.exp(-1j * (L - z) * np.sqrt(k ** 2 - 4 * np.pi ** 2 * (fx ** 2 + fy ** 2)))
    Uz = ifts(fts(sample) * E)

    # Distortion of the coordinates due to distance differences
    Mag_max = np.sqrt(W_c ** 2 / 2 + L ** 2) / z
    Dist_max = np.abs(Mag_max - Mag)
    camMat = np.array([[P, 0, P / 2], [0, Q, Q / 2], [0, 0, 1]])
    distCoeffs = np.array([-Dist_max / (2 * Mag), 0, 0, 0, 0])
    Uz = cv.undistort(np.angle(Uz).astype(np.float32), camMat, distCoeffs)

    return Uz


def ifts(A):
    return np.fft.ifftshift(np.fft.ifft2(np.fft.fftshift(A)))


def fts(A):
    return np.fft.ifftshift(np.fft.fft2(np.fft.fftshift(A)))


def resize(B, dx, dy):
    """cv2.resize for complex arrays (real and imaginary parts separately)."""
    r = cv.resize(np.real(B), (int(dx), int(dy)), interpolation=cv.INTER_LINEAR)
    i = cv.resize(np.imag(B), (int(dx), int(dy)), interpolation=cv.INTER_LINEAR)
    return r + 1j * i