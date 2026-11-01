import numpy as np
from models.parameters_enums import SplittingMethod

min_fragment = 10

def generate_mask(splitting_method, height, width, strips_vertical_n=None, strips_horizontal_n=None, strips_height=None, strips_width=None, equal_segments=True, even_width=True):
    mask = np.zeros((height, width))
    
    match splitting_method:
        case SplittingMethod.EVEN_VERTICAL:
            return even_vertical_mask(mask, width, strips_vertical_n, strips_width)
        case SplittingMethod.EVEN_HORIZONTAL:
            return even_horizontal_mask(mask, height, strips_horizontal_n, strips_height)
        case SplittingMethod.RANDOM_VERTICAL:
            return random_vertical_mask(mask, width, strips_vertical_n)
        case SplittingMethod.RANDOM_HORIZONTAL:
            return random_horizontal_mask(mask, height, strips_horizontal_n)
        case SplittingMethod.EVEN_RECTANGLES:
            new_mask = even_vertical_mask(mask, width, strips_vertical_n, strips_width)
            return even_horizontal_mask(new_mask, height, strips_horizontal_n, strips_height)
        case SplittingMethod.RANDOM_RECTANGLES:
            new_mask = random_vertical_mask(mask, width, strips_vertical_n)
            return random_horizontal_mask(new_mask, height, strips_horizontal_n)
        case SplittingMethod.SEGMENTED_STRIPS:
            return segmented_mask(mask, height, width, strips_vertical_n, strips_horizontal_n, equal_segments, even_width)
        case _:
            return np.zeros((height, width))

def random_normal_ints(low, high, size=1):
    mean = (low + high) / 2
    std = (high - low) / 6
    
    samples = np.random.normal(loc=mean, scale=std, size=size)
    ints = np.round(samples).astype(int)

    return np.clip(ints, low, high)

def random_cuts(val, max_strips, strips_n):
    # val should be the width for vertical cuts and height for horizontal cuts

    if strips_n is None:
        strips_n = int(random_normal_ints(2, max_strips, size=1)[0])

    strips_n = min(strips_n, max_strips)

    free_space = val - (strips_n * min_fragment)

    mean_width = free_space / strips_n
    std_dev = mean_width / 3
    
    samples = np.random.normal(loc=mean_width, scale=std_dev, size=strips_n)
    samples = np.clip(samples, 0.01, None) # getting rid of negative values
    samples_normalized = samples / np.sum(samples) # changing values to percentage of space
    extra_widths = np.round(samples_normalized * free_space).astype(int)

    # correcting the last strip
    diff = free_space - np.sum(extra_widths)
    extra_widths[np.argmax(extra_widths)] += diff

    # adding the minimal strip width
    widths = extra_widths + min_fragment
    
    cut_points = np.cumsum(widths)[:-1]

    return cut_points

def even_vertical_mask(mask, width, strips_n, strips_width):
    if strips_n is not None:
        strips_width = width // strips_n

    for j in range(strips_width, width, strips_width):
        if (j + min_fragment < width):
            mask[:, j] = 1       

    return mask

def random_vertical_mask(mask, width, strips_n):
    max_strips = width // min_fragment
    if max_strips < 1:
        return mask
    max_strips = min(20, max_strips)

    cut_points = random_cuts(width, max_strips, strips_n)

    for x in cut_points:
        mask[:, x] = 1

    return mask

def even_horizontal_mask(mask, height, strips_n, strips_height):
    if strips_n is not None:
        strips_height = height // strips_n

    for i in range(strips_height, height, strips_height):
        if (i+min_fragment < height):
            mask[i, :] = 1

    return mask

def random_horizontal_mask(mask, height, strips_n):
    max_strips = height // min_fragment
    if max_strips < 1:
        return mask
    max_strips = min(25, max_strips)

    cut_points = random_cuts(height, max_strips, strips_n)

    for x in cut_points:
        mask[x, :] = 1

    return mask

def segmented_mask(mask, height, width, strips_vertical_n, strips_horizontal_n, equal_segments, even_width):
    # vertical cuts
    max_strips = width // min_fragment
    if max_strips < 1:
        return mask
    max_strips = min(20, max_strips)
    
    if strips_vertical_n is None:
        strips_vertical_n = int(random_normal_ints(2, max_strips, size=1)[0])

    if even_width:
        strips_width = width // strips_vertical_n
        vertical_cut_points = np.arange(strips_width, width, strips_width, dtype=int)
    else:
        vertical_cut_points = random_cuts(width, max_strips, strips_vertical_n)

    for x in vertical_cut_points:
        mask[:, x] = 1

    # horizontal cuts
    max_strips = height // min_fragment
    if max_strips < 1:
        return mask
    max_strips = min(20, max_strips)

    if equal_segments and strips_horizontal_n is None:
        strips_horizontal_n = int(random_normal_ints(2, max_strips, size=1)[0])

    previous_cut = 0
    for cut in np.append(vertical_cut_points, width):
        if not equal_segments:
            strips_horizontal_n = int(random_normal_ints(2, max_strips, size=1)[0])

        horizontal_cut_points = random_cuts(height, max_strips, strips_horizontal_n)

        mask[horizontal_cut_points, previous_cut:cut] = 1

        previous_cut = cut

    return mask