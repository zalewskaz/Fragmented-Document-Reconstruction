import cv2
import numpy as np
from models.parameters_enums import SplittingMethod
import scipy.special

min_fragment = 20
min_area = 400

def generate_mask(splitting_method, height, width, strips_vertical_n=None, strips_horizontal_n=None, strips_height=None, strips_width=None, equal_segments=True, even_width=True, lines_n=5, points_k=0, hierarchical=False, points_n=5):
    mask = np.zeros((height, width), dtype=np.uint8)
    
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
        case SplittingMethod.STRAIGHT_POLYGONS:
            if hierarchical:
                return hierarchical_random_lines_mask(mask, height, width, lines_n)
            else:
                return polylines_mask(mask, height, width, lines_n, 0)
        case SplittingMethod.POLYLINE_POLYGONS:
            return polylines_mask(mask, height, width, lines_n, points_k)
        case SplittingMethod.VORONOI_POLYGONS:
            return voronoi_mask(mask, height, width, points_n)
        case SplittingMethod.BEZIER_CURVES:
            return polylines_mask(mask, height, width, lines_n, points_k, True)
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

def get_random_point_on_edge(edge, width, height):
    match edge:
        case 0: # Up
            return (np.random.randint(0, width), 0)
        case 1: # Right
            return (width - 1, np.random.randint(0, height))
        case 2: # Down
            return (np.random.randint(0, width), height - 1)
        case 3: # Left
            return (0, np.random.randint(0, height))

def is_cut_valid(mask):
    inverse_mask = np.where(mask == 0, 255, 0).astype(np.uint8)

    # stats for the created components
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(inverse_mask, connectivity=4)
    
    for i in range(1, num_labels):
        if stats[i, cv2.CC_STAT_AREA] < min_area:
            return False # too small part found
    return True

def hierarchical_random_lines_mask(mask, height, width, lines_n):
    cuts_done = 0
    attempts = 0
    max_attempts = 200

    while cuts_done < lines_n and attempts < max_attempts:
        # components statistics
        inverse_mask = np.where(mask == 0, 255, 0).astype(np.uint8)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(inverse_mask, connectivity=4)
        
        # selecting the biggest piece
        areas = stats[1:, cv2.CC_STAT_AREA]
        if len(areas) == 0: break
        largest_label = np.argmax(areas) + 1
        
        # checking if the biggest piece isn't too small
        if stats[largest_label, cv2.CC_STAT_AREA] < min_area * 2:
            break

        piece_mask = np.where(labels == largest_label, 1, 0).astype(np.uint8)
        
        # piece's bounding box
        x = stats[largest_label, cv2.CC_STAT_LEFT]
        y = stats[largest_label, cv2.CC_STAT_TOP]
        w = stats[largest_label, cv2.CC_STAT_WIDTH]
        h = stats[largest_label, cv2.CC_STAT_HEIGHT]
        
        # line cutting the piece
        edges = np.random.choice(4, size=2, replace=False)
        pt1_local = get_random_point_on_edge(edges[0], w, h)
        pt2_local = get_random_point_on_edge(edges[1], w, h)
        
        # drawing the line on the whole mask
        pt1 = (pt1_local[0] + x, pt1_local[1] + y)
        pt2 = (pt2_local[0] + x, pt2_local[1] + y)
        
        temp_line = np.zeros((height, width), dtype=np.uint8)
        cv2.line(temp_line, pt1, pt2, 1, thickness=1)
        segment_mask = cv2.bitwise_and(temp_line, piece_mask)
        temp_full_mask = cv2.bitwise_or(mask, segment_mask)
        
        if is_cut_valid(temp_full_mask):
            mask = temp_full_mask
            cuts_done += 1
            attempts = 0
        else:
            attempts += 1

    return mask

def polylines_mask(mask, height, width, lines_n, points_k, bezier=False):
    max_attempts = 200
    lines_drawn = 0
    attempts = 0

    while lines_drawn < lines_n:
        # two random edges and points on those edges
        edges = np.random.choice(4, size=2, replace=False)
        pt_start = get_random_point_on_edge(edges[0], width, height)
        pt_last = get_random_point_on_edge(edges[1], width, height)

        pts = [pt_start]
        for _ in range(points_k):
            pts.append((np.random.randint(0, width), np.random.randint(0, height)))
        pts.append(pt_last)
        pts_array = np.array(pts, np.int32).reshape((-1, 1, 2))

        if bezier:
            bezier_points = get_bezier_curve(pts, num_points=100)
            pts_array = bezier_points.reshape((-1, 1, 2))

        temp_mask = mask.copy()
        cv2.polylines(temp_mask, [pts_array], isClosed=False, color=1, thickness=1)

        if is_cut_valid(temp_mask):
            mask = temp_mask
            lines_drawn += 1
            attempts = 0
        else:
            attempts += 1

    return mask

def voronoi_mask(mask, height, width, points_n):
    # TODO: może dodać manhattan distance, ale wtedy już nie z biblioteką cv2
    
    rect = (0, 0, width, height)
    subdiv = cv2.Subdiv2D(rect)
    
    accepted_points = []
    attempts = 0
    max_attempts = 1000
    min_dist = 50

    while len(accepted_points) < points_n and attempts < max_attempts:
        x = np.random.randint(0, width)
        y = np.random.randint(0, height)
        new_point = np.array([x, y])
        
        if len(accepted_points) == 0:
            accepted_points.append(new_point)
            subdiv.insert((int(x), int(y)))
        else:
            distances = np.linalg.norm(np.array(accepted_points) - new_point, axis=1)
            
            if np.all(distances >= min_dist):
                accepted_points.append(new_point)
                subdiv.insert((int(x), int(y)))
                attempts = 0
            else:
                attempts += 1
        
    facets, centers = subdiv.getVoronoiFacetList([])
    
    for facet in facets:
        pts = np.array(facet, dtype=np.int32)
        cv2.polylines(mask, [pts], isClosed=True, color=1, thickness=1)
        
    return mask

def get_bezier_curve(points, num_points=100):
    n = len(points) - 1
    t = np.linspace(0, 1, num_points)
    curve = np.zeros((num_points, 2))
    
    for i, pt in enumerate(points):
        binomial_coeff = scipy.special.comb(n, i)
        term = binomial_coeff * ((1 - t) ** (n - i)) * (t ** i)
        
        curve[:, 0] += term * pt[0]
        curve[:, 1] += term * pt[1]
        
    return curve.astype(np.int32)