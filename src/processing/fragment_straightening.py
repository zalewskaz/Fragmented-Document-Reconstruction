import cv2
import numpy as np
from models import ImageFragment
from .fragment_rotation import rotate_fragment

MAX_RECTANGLE_DEVIATION = 3.0

def straighten_fragment(
    fragment: ImageFragment,
    max_deviation: float = MAX_RECTANGLE_DEVIATION
) -> tuple[ImageFragment, bool]:
    """
    Rotates a rectangular fragment so its sides are horizontal and vertical.

    The smallest rotated rectangle containing the fragment (cv2.minAreaRect) gives the angle the fragment
    is tilted by. The fragment counts as a rectangle if its outline lies within `max_deviation` pixels
    of the sides of that rectangle (see `rectangle_deviation`). Only rectangles are rotated -
    for other shapes the angle of the enclosing rectangle doesn't mean anything.

    The angle is only known up to a multiple of 90 degrees, so the fragment is rotated by the smallest
    angle that makes its sides axis-aligned; whether its content is upright, sideways or upside down
    stays unknown.

    Args:
        fragment (ImageFragment): The fragment in BGRA format, with transparent background (alpha 0).
        max_deviation (float, optional): The maximum distance (in pixels) of the outline from the sides
                                         of the enclosing rectangle for the fragment to count as a rectangle.

    Returns:
        tuple[ImageFragment, bool]:
            - the straightened fragment (or the unchanged one, if it isn't a rectangle),
            - whether the fragment is a rectangle.
    """
    contour = largest_contour(fragment)
    if contour is None:
        return fragment, False

    rect = cv2.minAreaRect(contour)
    if rectangle_deviation(contour, rect) > max_deviation:
        return fragment, False

    # minAreaRect returns the angle from a different range depending on the OpenCV version;
    # modulo 90 it's always the same, so it's brought to (-45, 45] - the smallest rotation that straightens the sides
    angle = rect[2]
    correction = (angle + 45) % 90 - 45
    if abs(correction) < 1e-6:
        return fragment, True

    return rotate_fragment(fragment, correction), True

def straighten_fragments(
    fragments: list[ImageFragment],
    max_deviation: float = MAX_RECTANGLE_DEVIATION,
    stop_callback=None
) -> list[tuple[ImageFragment, bool]]:
    """
    Straightens every fragment in the list (see `straighten_fragment`).

    Args:
        fragments (list[ImageFragment]): The fragments to straighten.
        max_deviation (float, optional): See `straighten_fragment`.
        stop_callback (callable, optional): Function returning True if the user pressed Stop -
                                            checked before each fragment; the fragments done so far are returned.

    Returns:
        list[tuple[ImageFragment, bool]]: For each fragment: the straightened fragment and whether it's a rectangle.
    """
    results = []
    for fragment in fragments:
        if stop_callback is not None and stop_callback():
            break
        results.append(straighten_fragment(fragment, max_deviation))
    return results

def largest_contour(fragment: ImageFragment) -> np.ndarray | None:
    """Returns the outer contour of the biggest opaque area of the fragment, or None if it's fully transparent."""
    mask = (fragment.data[..., 3] > 0).astype(np.uint8)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        return None
    return max(contours, key=cv2.contourArea)

def rectangle_deviation(contour: np.ndarray, rect, percentile: float = 98) -> float:
    """
    Returns how far (in pixels) the contour lies from the sides of the rectangle.

    It's the given percentile of the distances of the contour points, not the maximum: single pixels
    sticking out or missing on the edge (e.g. left by the extraction) would otherwise make a rectangle
    count as some other shape. A real difference in shape, like a cut corner, moves many points.

    Args:
        contour (np.ndarray): Contour from cv2.findContours (with CHAIN_APPROX_NONE), shape (N, 1, 2).
        rect: The rotated rectangle from cv2.minAreaRect.
        percentile (float, optional): Which percentile of the distances to return.

    Returns:
        float: The distance; close to 0 if the contour is the rectangle.
    """
    box = cv2.boxPoints(rect).astype(np.float32).reshape(-1, 1, 2)
    distances = [
        abs(cv2.pointPolygonTest(box, (float(point[0][0]), float(point[0][1])), True))
        for point in contour
    ]
    return float(np.percentile(distances, percentile))
