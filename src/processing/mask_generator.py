import cv2
import numpy as np
from models.parameters_enums import SplittingMethod
import scipy.special

MIN_FRAGMENT_WIDTH = 20
MIN_FRAGMENT_AREA = 400
MAX_ATTEMPTS = 400

def generate_mask(splitting_method, height, width, strips_vertical_n=None, strips_horizontal_n=None, 
                  strips_height=None, strips_width=None, equal_segments=True, even_width=True, lines_n=5, 
                  points_k=0, hierarchical=False, points_n=5, warning_callback=None):
    """
    Generates a mask for splitting a document using a selected method.

    Args:
        splitting_method (SplittingMethod): Algorithm method to use for document splitting.
        height (int): Height of the image matrix.
        width (int): Width of the image matrix.
        strips_vertical_n (int, optional): Number of vertical strips.
        strips_horizontal_n (int, optional): Number of horizontal strips.
        strips_height (int, optional): Height of individual strips.
        strips_width (int, optional): Width of individual strips.
        equal_segments (bool, optional): Whether to divide strips into the same number of segments (in SEGMENTED_STRIPS).
        even_width (bool, optional): Whether to cut the document into strips of equal width (in SEGMENTED_STRIPS).
        lines_n (int, optional): Number of lines to be drawn.
        points_k (int, optional): Number of vertices in a single line (in POLYLINES_POLYGON).
        hierarchical (bool, optional): Whether to use recursive cutting for straight-edge polygons.
        points_n (int, optional): Number of center points (in VORONOI_POLYGONS).
        warning_callback (callable, optional): Function to display a UI pop-up warning.

    Returns:
        np.ndarray: Binary mask matrix where 1 represents a cut and 0 represents the background.
    """
    
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
                return hierarchical_random_lines_mask(mask, height, width, lines_n, warning_callback)
            else:
                return polylines_mask(mask, height, width, lines_n, 0, warning_callback)
        case SplittingMethod.POLYLINE_POLYGONS:
            return polylines_mask(mask, height, width, lines_n, points_k, warning_callback)
        case SplittingMethod.VORONOI_POLYGONS:
            return voronoi_mask(mask, height, width, points_n, warning_callback)
        case SplittingMethod.BEZIER_CURVES:
            return polylines_mask(mask, height, width, lines_n, points_k, warning_callback, True)
        case _:
            return np.zeros((height, width))

def random_normal_ints(low, high, size=1):
    """
    Samples a selected number of integers from a normal distribution.

    Args:
        low (int): The minimum expected value (lower bound) of the distribution.
        high (int): The maximum expected value (upper bound) of the distribution.
        size (int, optional): Number of integers to sample. Defaults to 1.

    Returns:
        np.ndarray: Sampled integers.
    """

    mean = (low + high) / 2
    std = (high - low) / 6
    
    samples = np.random.normal(loc=mean, scale=std, size=size)
    ints = np.round(samples).astype(int)

    return np.clip(ints, low, high)

def random_cuts(val, max_strips, strips_n):
    """
    Samples random vertical or horizontal cuts from the normal distribution.

    Args:
        val (int): Width of the fragment for vertical cuts and height of the fragment for horizontal cuts.
        max_strips (int): Maximum number of strips that can fit in the given space.
        strips_n (int): Number of strips to create.

    Returns:
        np.ndarray: List of sampled cutting points.
    """

    # drawing a random number of strips of it wasn't given
    if strips_n is None:
        strips_n = int(random_normal_ints(2, max_strips, size=1)[0])

    # asserting that all strips can fit
    strips_n = min(strips_n, max_strips)

    # calculating the remaining free space if not for our minimmum fragment width
    free_space = val - (strips_n * MIN_FRAGMENT_WIDTH)

    mean_width = free_space / strips_n
    std_dev = mean_width / 3

    # drawing random cut places from the normal distribution
    samples = np.random.normal(loc=mean_width, scale=std_dev, size=strips_n)
    samples = np.clip(samples, 0.01, None) # getting rid of negative values
    samples_normalized = samples / np.sum(samples) # changing values to percentage of space
    extra_widths = np.round(samples_normalized * free_space).astype(int)

    # correcting the last strip
    diff = free_space - np.sum(extra_widths)
    extra_widths[np.argmax(extra_widths)] += diff

    # adding the minimal strip width
    widths = extra_widths + MIN_FRAGMENT_WIDTH
    
    cut_points = np.cumsum(widths)[:-1]

    return cut_points

def even_vertical_mask(mask, width, strips_n, strips_width):
    """
    Creates a mask with even vertical strips.

    Args:
        mask (np.ndarray): Matrix to draw the created mask on.
        width (int): Width of the image matrix.
        strips_n (int): Number of vertical strips.
        strips_width (int): Width of individual strips.

    Returns:
        np.ndarray: Binary mask matrix where 1 represents a cut and 0 represents the background.
    """

    # calculating the strips' width if only their number was given
    if strips_n is not None:
        strips_width = width // strips_n

    # drawing the mask
    for j in range(strips_width, width, strips_width):
        if (j + MIN_FRAGMENT_WIDTH < width):
            mask[:, j] = 1       

    return mask

def random_vertical_mask(mask, width, strips_n):
    """
    Creates a mask with vertical strips of random width.

    Args:
        mask (np.ndarray): Matrix to draw the created mask on.
        width (int): Width of the image matrix.
        strips_n (int): Number of vertical strips.

    Returns:
        np.ndarray: Binary mask matrix where 1 represents a cut and 0 represents the background.
    """

    # asserting that all the cuts can fit
    max_strips = width // MIN_FRAGMENT_WIDTH
    if max_strips < 1:
        return mask
    max_strips = min(20, max_strips)

    # sampling random cut points
    cut_points = random_cuts(width, max_strips, strips_n)

    for x in cut_points:
        mask[:, x] = 1

    return mask

def even_horizontal_mask(mask, height, strips_n, strips_height):
    """
    Creates a mask with even horizontal strips.

    Args:
        mask (np.ndarray): Matrix to draw the created mask on.
        height (int): Height of the image matrix.
        strips_n (int): Number of horizontal strips.
        strips_height (int): Height of individual strips.

    Returns:
        np.ndarray: Binary mask matrix where 1 represents a cut and 0 represents the background.
    """

    # calculating the strips' height if only their number was given
    if strips_n is not None:
        strips_height = height // strips_n

    # drawing the mask
    for i in range(strips_height, height, strips_height):
        if (i+MIN_FRAGMENT_WIDTH < height):
            mask[i, :] = 1

    return mask

def random_horizontal_mask(mask, height, strips_n):
    """
    Creates a mask with horizontal strips of random height.

    Args:
        mask (np.ndarray): Matrix to draw the created mask on.
        height (int): Height of the image matrix.
        strips_n (int): Number of horizontal strips.

    Returns:
        np.ndarray: Binary mask matrix where 1 represents a cut and 0 represents the background.
    """

    # asserting that all the cuts can fit
    max_strips = height // MIN_FRAGMENT_WIDTH
    if max_strips < 1:
        return mask
    max_strips = min(25, max_strips)

    # drawing random cut points
    cut_points = random_cuts(height, max_strips, strips_n)

    for x in cut_points:
        mask[x, :] = 1

    return mask

def segmented_mask(mask, height, width, strips_vertical_n, strips_horizontal_n, equal_segments, even_width):
    """
    Creates a mask with segmented strips (vertical cuts individually cut into segments).

    Args:
        mask (np.ndarray): Matrix to draw the created mask on.
        height (int): Height of the image matrix.
        width (int): Width of the image matrix.
        strips_vertical_n (int): Number of vertical strips.
        strips_horizontal_n (int): Number of horizontal segments.
        equal_segments (bool): Whether to divide strips into the same number of segments.
        even_width (bool): Whether to cut the document into strips of equal width.

    Returns:
        np.ndarray: Binary mask matrix where 1 represents a cut and 0 represents the background.
    """

    # vertical cuts

    # asserting that all the cuts can fit
    max_strips = width // MIN_FRAGMENT_WIDTH
    if max_strips < 1:
        return mask
    max_strips = min(30, max_strips)

    # drawing a random number of strips if it wasn't given
    if strips_vertical_n is None:
        strips_vertical_n = int(random_normal_ints(2, max_strips, size=1)[0])

    if even_width:
        # cutting into even strips
        strips_width = width // strips_vertical_n
        vertical_cut_points = np.arange(strips_width, width, strips_width, dtype=int)

        # asserting that the last strip is big enough
        if len(vertical_cut_points) > 0:
            if width - vertical_cut_points[-1] < MIN_FRAGMENT_WIDTH:
                vertical_cut_points = vertical_cut_points[:-1]
    else:
        # cutting into random strips
        vertical_cut_points = random_cuts(width, max_strips, strips_vertical_n)

    for x in vertical_cut_points:
        mask[:, x] = 1

    # horizontal cuts

    # asserting that all the cuts can fit
    max_strips = height // MIN_FRAGMENT_WIDTH
    if max_strips < 1:
        return mask
    max_strips = min(20, max_strips)

    # drawing a random number of segments if it wasn't given
    if equal_segments and strips_horizontal_n is None:
        strips_horizontal_n = int(random_normal_ints(2, max_strips, size=1)[0])

    # adding the cuts to each strip
    previous_cut = 0
    for cut in np.append(vertical_cut_points, width):
        if not equal_segments:
            # drawing random number of segments if they aren't of equal height
            strips_horizontal_n = int(random_normal_ints(2, max_strips, size=1)[0])

        # drawing random cutting points
        horizontal_cut_points = random_cuts(height, max_strips, strips_horizontal_n)

        mask[horizontal_cut_points, previous_cut:cut] = 1

        previous_cut = cut

    return mask

def get_random_point_on_edge(edge, width, height):
    """
    Samples a random point on a selected edge of a matrix.

    Args:
        edge (int): An integer from 0 to 3 indicating the target edge (0: Top, 1: Right, 2: Bottom, 3: Left).
        width (int): Width of the matrix.
        haight (int): Height of the matrix.

    Returns:
        tuple[int, int]: The (x, y) coordinates of the generated point.
    """

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
    """
    Checks if the matrix has only valid fragments (of areas bigger than MIN_FRAGMENT_AREA)

    Args:
        mask (np.ndarray): Matrix to check.

    Returns:
        boolean: Whether the mask has only valid fragments.
    """
    
    inverse_mask = np.where(mask == 0, 255, 0).astype(np.uint8)

    # stats for the created components
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(inverse_mask, connectivity=4)
    
    for i in range(1, num_labels):
        if stats[i, cv2.CC_STAT_AREA] < MIN_FRAGMENT_AREA:
            return False # too small part found
    return True

def hierarchical_random_lines_mask(mask, height, width, lines_n, warning_callback):
    """
    Creates a mask with straight-edge polygons by recursively cutting the biggest fragment in two.

    Args:
        mask (np.ndarray): Matrix to draw the created mask on.
        height (int): Height of the image matrix.
        width (int): Width of the image matrix.
        lines_n (int): Number of lines (cuts) to generate.
        warning_callback (callable, optional): Function to display a UI pop-up warning for time limit exceeded.

    Returns:
        np.ndarray: Binary mask matrix where 1 represents a cut and 0 represents the background.
    """

    cuts_done = 0
    attempts = 0

    while cuts_done < lines_n and attempts < MAX_ATTEMPTS:
        # components statistics
        inverse_mask = np.where(mask == 0, 255, 0).astype(np.uint8)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(inverse_mask, connectivity=4)
        
        # selecting the biggest piece
        areas = stats[1:, cv2.CC_STAT_AREA]
        if len(areas) == 0: break
        largest_label = np.argmax(areas) + 1
        
        # checking if the biggest piece isn't too small
        if stats[largest_label, cv2.CC_STAT_AREA] < MIN_FRAGMENT_AREA * 2:
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

        # checking whether the cut creates all valid elements
        if is_cut_valid(temp_full_mask):
            mask = temp_full_mask
            cuts_done += 1
            attempts = 0
        else:
            attempts += 1

    # when the number of attempts excedded max attempts
    if cuts_done != lines_n:
        if warning_callback is not None:
            warning_callback(f"Time limit exceeded. Only {cuts_done} out of {lines_n} lines were drawn.")

    return mask

def get_bezier_curve(points, num_points=100):
    """
    Changes a polyline defined by a set of points into a Bezier curve.

    Args:
        points (np.ndarray): Set of control points defining the curve.
        num_points (int, optional): Number of points to generate along the curve, determining its resolution/smoothness. Defaults to 100.

    Returns:
        np.ndarray: An array of shape (num_points, 2) containing the integer (x, y) coordinates of the calculated Bezier curve.
    """

    n = len(points) - 1
    t = np.linspace(0, 1, num_points)
    curve = np.zeros((num_points, 2))
    
    for i, pt in enumerate(points):
        binomial_coeff = scipy.special.comb(n, i)
        term = binomial_coeff * ((1 - t) ** (n - i)) * (t ** i)
        
        curve[:, 0] += term * pt[0]
        curve[:, 1] += term * pt[1]
        
    return curve.astype(np.int32)

def polylines_mask(mask, height, width, lines_n, points_k, warning_callback, bezier=False):
    """
    Creates a mask with straight-edge polygons by drawing polylines or curves.

    Args:
        mask (np.ndarray): Matrix to draw the created mask on.
        height (int): Height of the image matrix.
        width (int): Width of the image matrix.
        lines_n (int): Number of lines (cuts) to generate.
        points_k (int): Number of vertices in a single line.
        warning_callback (callable, optional): Function to display a UI pop-up warning for time limit exceeded.
        bezier (boolean, optional): Whether to change the polylines into Bezier curves.

    Returns:
        np.ndarray: Binary mask matrix where 1 represents a cut and 0 represents the background.
    """

    lines_drawn = 0
    attempts = 0

    while lines_drawn < lines_n and attempts < MAX_ATTEMPTS:
        # two random edges and points on those edges
        edges = np.random.choice(4, size=2, replace=False)
        pt_start = get_random_point_on_edge(edges[0], width, height)
        pt_last = get_random_point_on_edge(edges[1], width, height)

        # adding random vertices to the line
        pts = [pt_start]
        for _ in range(points_k):
            pts.append((np.random.randint(0, width), np.random.randint(0, height)))
        pts.append(pt_last)
        pts_array = np.array(pts, np.int32).reshape((-1, 1, 2))

        # changing the polyline into a curve if this option is selected
        if bezier:
            bezier_points = get_bezier_curve(pts, num_points=100)
            pts_array = bezier_points.reshape((-1, 1, 2))

        # drawing the polylines/curves
        temp_mask = mask.copy()
        cv2.polylines(temp_mask, [pts_array], isClosed=False, color=1, thickness=1)

        # checking whether the cut creates all valid elements
        if is_cut_valid(temp_mask):
            mask = temp_mask
            lines_drawn += 1
            attempts = 0
        else:
            attempts += 1

    # when the number of attempts excedded max attempts
    if lines_drawn != lines_n:
        if warning_callback is not None:
            warning_callback(f"Time limit exceeded. Only {lines_drawn} out of {lines_n} lines were drawn.")

    return mask

def voronoi_mask(mask, height, width, points_n, warning_callback):
    """
    Creates a mask with polygons by using Voronoi tesselation.

    Args:
        mask (np.ndarray): Matrix to draw the created mask on.
        height (int): Height of the image matrix.
        width (int): Width of the image matrix.
        points_n (int): Number of center points.
        warning_callback (callable, optional): Function to display a UI pop-up warning for time limit exceeded.

    Returns:
        np.ndarray: Binary mask matrix where 1 represents a cut and 0 represents the background.
    """

    # TODO: maybe add manhattan distance, but that has to be done without the cv2 library
    
    # preparing a from for the division
    rect = (0, 0, width, height)
    subdiv = cv2.Subdiv2D(rect)
    
    accepted_points = []
    attempts = 0
    min_dist = 50

    while len(accepted_points) < points_n and attempts < MAX_ATTEMPTS*4:
        # finding a random point on the matrix
        x = np.random.randint(0, width)
        y = np.random.randint(0, height)
        new_point = np.array([x, y])

        # adding the point to our list
        if len(accepted_points) == 0:
            accepted_points.append(new_point)
            subdiv.insert((int(x), int(y)))
        else:
            # checking to see if the points aren't too close to each other
            distances = np.linalg.norm(np.array(accepted_points) - new_point, axis=1)
            
            if np.all(distances >= min_dist):
                accepted_points.append(new_point)
                subdiv.insert((int(x), int(y)))
                attempts = 0
            else:
                attempts += 1

    # when the number of attempts excedded max attempts
    if len(accepted_points) != points_n:
        if warning_callback is not None:
            warning_callback(f"Time limit exceeded. Only {len(accepted_points)} out of {points_n} centers used.")

    # divide the matrix using Voronoi tesselation
    facets, centers = subdiv.getVoronoiFacetList([])

    # draw the divide
    for facet in facets:
        pts = np.array(facet, dtype=np.int32)
        cv2.polylines(mask, [pts], isClosed=True, color=1, thickness=1)
        
    return mask