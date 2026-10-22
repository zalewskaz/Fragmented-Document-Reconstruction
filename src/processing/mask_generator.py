import numpy
from models.parameters_enums import SplittingMethod

def generate_mask(splitting_method, heigth, width, stripes_vertical_n=None, stripes_horizontal_n=None, stripes_height=None, stripes_width=None):
    match splitting_method:
        case SplittingMethod.EVEN_VERTICAL:
            return even_vertical_mask(heigth, width, stripes_vertical_n, stripes_width)
        case SplittingMethod.EVEN_HORIZONTAL:
            return even_horizontal_mask(heigth, width, stripes_horizontal_n, stripes_height)
        case _:
            return numpy.zeros((heigth, width))

def even_vertical_mask(heigth, width, stripes_n, stripes_width):
    mask = numpy.zeros((heigth, width))

    if stripes_n is not None:
        stripes_width = width // stripes_n
    for j in range(stripes_width, width, stripes_width):
        for i in range(heigth):
            mask[i, j] = 1

    return mask

def even_horizontal_mask(height, width, stripes_n, stripes_height):
    mask = numpy.zeros((height, width))
    
    if stripes_n is not None:
        stripes_height = height // stripes_n
    for i in range(stripes_height, height, stripes_height):
        for j in range(width):
            mask[i, j] = 1

    return mask