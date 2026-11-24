import cv2
import numpy as np
from models import ImageFragment
from .fragment_rotation import rotate_fragment

MIN_RECTANGLE_FILL = 0.9

def straighten_fragment(fragment: ImageFragment) -> tuple[ImageFragment, bool]:
    """
    Rotates a rectangular fragment so its sides are horizontal and vertical.

    The smallest rotated rectangle containing the fragment (cv2.minAreaRect) gives the angle the fragment
    is tilted by. Only rectangles are rotated (see `is_rectangle`) - for other shapes the angle of
    the enclosing rectangle doesn't mean anything.

    The angle is only known up to a multiple of 90 degrees, so the fragment is rotated by the smallest
    angle that makes its sides axis-aligned; whether its content is upright, sideways or upside down
    stays unknown.

    Args:
        fragment (ImageFragment): The fragment in BGRA format, with transparent background (alpha 0).

    Returns:
        tuple[ImageFragment, bool]:
            - the straightened fragment (or the unchanged one, if it isn't a rectangle),
            - whether the fragment is a rectangle.
    """
    contour = largest_contour(fragment)
    if contour is None:
        return fragment, False

    rect = cv2.minAreaRect(contour)
    if not is_rectangle(contour, rect):
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
    stop_callback=None
) -> list[tuple[ImageFragment, bool]]:
    """
    Straightens every fragment in the list (see `straighten_fragment`).

    Args:
        fragments (list[ImageFragment]): The fragments to straighten.
        stop_callback (callable, optional): Function returning True if the user pressed Stop -
                                            checked before each fragment; the fragments done so far are returned.

    Returns:
        list[tuple[ImageFragment, bool]]: For each fragment: the straightened fragment and whether it's a rectangle.
    """
    results = []
    for fragment in fragments:
        if stop_callback is not None and stop_callback():
            break
        results.append(straighten_fragment(fragment))
    return results

def is_rectangle(contour: np.ndarray, rect) -> bool:
    """
    Whether the contour is a rectangle: it fills at least MIN_RECTANGLE_FILL of the rotated rectangle `rect`
    (the smallest one around it).

    A rectangle fills all of it; rectangles damaged by the extraction (a notch, corners rounded by
    the brightness threshold method) still fill nearly all of it, while other shapes leave much more
    of it empty (a hexagon 25%, a triangle half).

    Args:
        contour (np.ndarray): Contour from cv2.findContours, shape (N, 1, 2).
        rect: The rotated rectangle from cv2.minAreaRect.

    Returns:
        bool: Whether it's a rectangle.
    """
    width, height = rect[1]
    if width * height == 0:
        return False
    return cv2.contourArea(contour) / (width * height) >= MIN_RECTANGLE_FILL

def largest_contour(fragment: ImageFragment) -> np.ndarray | None:
    """Returns the outer contour of the biggest opaque area of the fragment, or None if it's fully transparent."""
    mask = (fragment.data[..., 3] > 0).astype(np.uint8)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        return None
    return max(contours, key=cv2.contourArea)
