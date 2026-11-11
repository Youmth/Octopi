import numpy as np

from core import DEFAULT_COSINE_PERIOD
from core.propagation import normalize, propagate
from core.kreuzer import filtcosenoF, kreuzer3F
import time


def reconstruct(input_dict):
    init_time = time.time()

    field = np.sqrt(normalize(input_dict['image'], 1))

    FC = filtcosenoF(DEFAULT_COSINE_PERIOD, np.array((field.shape[1], field.shape[0])))

    if input_dict['algorithm'] == 'AS':
        recon = propagate(field,
                          input_dict['r'],
                          input_dict['wavelength'],
                          input_dict['dxy'],
                          input_dict['dxy'],
                          input_dict['scale_factor'])
    elif input_dict['algorithm'] == 'KR':

        Z = input_dict['Z']
        L = input_dict['L']
        dxy = input_dict['dxy']

        deltaX = Z * dxy / L
        recon = kreuzer3F(field, Z, L, input_dict['wavelength'], dxy, deltaX, FC)

    sq = input_dict['squared']
    ph = input_dict['phase']

    recon = np.zeros((2, 2), np.complex64)
    if sq:
        arr = normalize(np.abs(recon) ** 2, 255)
    elif not sq and ph:
        arr = normalize(np.angle(recon), 255)
    else:
        arr = normalize(np.abs(recon), 255)

    # if input_dict['filters']:
    #     filter_functions = input_dict['filters'][0]
    #     filter_params = input_dict['filters'][1]
    #
    #     if input_dict['filter']:
    #         for filter, param, in zip(filter_functions, filter_params):
    #             filt_img = filter_dict[filter](filt_img, param)

    # filt_img = arr2im(filt_img.astype(np.uint8))
    # filt_img = create_image(filt_img, field.shape[1], field.shape[0])

    end_time = time.time()
    elapsed_time = end_time - init_time
    fps = round(1 / elapsed_time, 1) if elapsed_time != 0 else 0

    return arr, fps
