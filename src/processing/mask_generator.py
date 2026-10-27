import numpy as np
from models.parameters_enums import SplittingMethod

min_fragment = 10

def generate_mask(splitting_method, height, width, stripes_vertical_n=None, stripes_horizontal_n=None, stripes_height=None, stripes_width=None):
    match splitting_method:
        case SplittingMethod.EVEN_VERTICAL:
            return even_vertical_mask(height, width, stripes_vertical_n, stripes_width)
        case SplittingMethod.EVEN_HORIZONTAL:
            return even_horizontal_mask(height, width, stripes_horizontal_n, stripes_height)
        case SplittingMethod.RANDOM_VERTICAL:
            return random_vertical_mask(height, width, stripes_vertical_n)
        case SplittingMethod.RANDOM_HORIZONTAL:
            return random_horizontal_mask(height, width, stripes_horizontal_n)
        case _:
            return np.zeros((height, width))

def random_normal_ints(low, high, size=1):
    mean = (low + high) / 2
    std = (high - low) / 6
    
    samples = np.random.normal(loc=mean, scale=std, size=size)
    ints = np.round(samples).astype(int)

    return np.clip(ints, low, high)

def even_vertical_mask(height, width, stripes_n, stripes_width):
    mask = np.zeros((height, width))

    if stripes_n is not None:
        stripes_width = width // stripes_n
    for j in range(stripes_width, width, stripes_width):
        if (j+min_fragment < width):
            for i in range(height):
                mask[i, j] = 1

    return mask

def random_vertical_mask(height, width, stripes_n):
    mask = np.zeros((height, width))

    max_stripes = width // min_fragment
    if max_stripes < 1:
        return mask

    if stripes_n is None:
        stripes_n = int(random_normal_ints(2, min(30, max_stripes), size=1)[0])

    stripes_n = min(stripes_n, max_stripes)

    free_space = width - (stripes_n * min_fragment)

    mean_width = free_space / stripes_n
    std_dev = mean_width / 3
    
    samples = np.random.normal(loc=mean_width, scale=std_dev, size=stripes_n)
    samples = np.clip(samples, 0.01, None) # getting rid of negative values
    samples_normalized = samples / np.sum(samples) # changing values to percentage of space
    extra_widths = np.round(samples_normalized * free_space).astype(int)

    # correcting the last stripe
    diff = free_space - np.sum(extra_widths)
    extra_widths[np.argmax(extra_widths)] += diff

    # adding the minimal stripe width
    widths = extra_widths + min_fragment
    
    cut_points = np.cumsum(widths)[:-1]

    for x in cut_points:
        mask[:, x] = 1

    return mask

def even_horizontal_mask(height, width, stripes_n, stripes_height):
    mask = np.zeros((height, width))
    
    if stripes_n is not None:
        stripes_height = height // stripes_n
    for i in range(stripes_height, height, stripes_height):
        if (i+min_fragment < height):
            for j in range(width):
                mask[i, j] = 1

    return mask

def random_horizontal_mask(height, width, stripes_n):
    mask = np.zeros((height, width))

    max_stripes = height // min_fragment
    if max_stripes < 1:
        return mask

    if stripes_n is None:
        stripes_n = int(random_normal_ints(2, min(40, max_stripes), size=1)[0])

    stripes_n = min(stripes_n, max_stripes)

    free_space = height - (stripes_n * min_fragment)

    mean_width = free_space / stripes_n
    std_dev = mean_width / 3
    
    samples = np.random.normal(loc=mean_width, scale=std_dev, size=stripes_n)
    samples = np.clip(samples, 0.01, None) # getting rid of negative values
    samples_normalized = samples / np.sum(samples) # changing values to percentage of space
    extra_widths = np.round(samples_normalized * free_space).astype(int)

    # correcting the last stripe
    diff = free_space - np.sum(extra_widths)
    extra_widths[np.argmax(extra_widths)] += diff

    # adding the minimal stripe width
    widths = extra_widths + min_fragment
    
    cut_points = np.cumsum(widths)[:-1]

    for x in cut_points:
        mask[x, :] = 1

    return mask