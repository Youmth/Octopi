from PIL import Image
import numpy as np


def im2arr(path: str):
    '''Converts file image into numpy array.'''
    return np.asarray(Image.open(path).convert('L'))

def arr2im(array: np.ndarray):
    '''Converts numpy array into PhotoImage type'''
    return Image.fromarray(array.astype(np.uint8), 'L')

def load_grayscale(path:str) -> np.ndarray:
    """Load an image file as a 2D grayscale array"""
    with Image.open(path) as img:
        return np.asarray(img.convert("L"))
