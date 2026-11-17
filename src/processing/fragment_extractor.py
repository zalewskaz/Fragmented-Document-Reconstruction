import cv2
import numpy as np
from models import ImageFragment, EdgePixelAttributionOption, ExtractionMethod
from .image_splitter import split_image

def get_fragment_contours(
    original_image: np.ndarray,
    method: str = ExtractionMethod.FLOOD_FILL.value,
    min_fragment_area: int = 100,
    tolerance: int = 10,
    closing_kernel_size: int = 21
) -> tuple[np.ndarray, np.ndarray]:
    """
    Extracts fragments' contours using the selected method and creates contour masks.

    Args:
        original_image (np.ndarray): Image with fragments to find.
        method (str): Name of the selected extraction method.
        min_fragment_area (int): Minimal area of the fragments on the image in pixels.
        tolerance (int): Maximum color difference allowed when flooding the background (used only in FLOOD_FILL method).
        closing_kernel_size (int): Size of the structural element used for morphological closing to fill gaps (used only in OTSU method).

    Returns:
        tuple[np.ndarray, np.ndarray]: A tuple containing two masks:
            - fragments_mask (np.ndarray): Binary mask matrix where 1 represents a fragment 
              and 0 represents the background.
            - contour_mask (np.ndarray): Binary mask matrix where 1 represents the fragments' 
              contours and 0 represents the space inside or outside of the fragments.
    """
    
    if method == ExtractionMethod.FLOOD_FILL.value:
        foreground = flood_fill_foreground(original_image, tolerance)
    elif method == ExtractionMethod.OTSU.value:
        foreground = otsu_foreground(original_image, closing_kernel_size)
    else:
        raise ValueError(f"Unknown extraction method: {method}")

    height, width = original_image.shape[:2]
    fragments_mask = np.zeros((height, width), dtype=np.uint8)
    contour_mask = np.zeros((height, width), dtype=np.uint8)

    contours, _ = cv2.findContours(foreground, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [c for c in contours if cv2.contourArea(c) >= min_fragment_area]

    cv2.drawContours(fragments_mask, contours, -1, 1, cv2.FILLED)
    cv2.drawContours(contour_mask, contours, -1, 1, 1)

    return fragments_mask, contour_mask

def flood_fill_foreground(original_image: np.ndarray, tolerance: int = 10) -> np.ndarray:
    """
    Floods the image's background to find the fragments' contours.

    Args:
        original_image (np.ndarray): Image with fragments to find.
        tolerance (int): Maximum color difference allowed when flooding the background.

    Returns:
        np.ndarray: Binary mask of the foreground where 1 represents the fragments and 0 represents the background.
    """

    if original_image.ndim == 2:
        pixels = np.ascontiguousarray(original_image)
    else:
        pixels = np.ascontiguousarray(original_image[..., :3])

    bg_colour = border_median_colour(pixels)
    framed = cv2.copyMakeBorder(pixels, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=bg_colour)

    height, width = framed.shape[:2]
    flood_mask = np.zeros((height + 2, width + 2), dtype=np.uint8)
    flags = 4 | cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE | (1 << 8)
    diff = (tolerance,) * 3
    cv2.floodFill(framed, flood_mask, (0, 0), 0, diff, diff, flags)

    background = flood_mask[2:-2, 2:-2]
    return (background == 0).astype(np.uint8)

def otsu_foreground(original_image: np.ndarray, closing_kernel_size: int = 21) -> np.ndarray:
    """
    Finds the frgaments' borders using binarization with an Otsu threshold.

    Args:
        original_image (np.ndarray): Image with fragments to find.
        closing_kernel_size (int): Size of the structural element used for morphological closing to fill gaps.

    Returns:
        np.ndarray: Binary mask of the foreground where 1 represents the fragments and 0 represents the background.
    """

    gray = to_grayscale(original_image)

    # the background is what lies on the image border; checking only one corner
    # would fail when a fragment happens to lie there
    if border_median_colour(gray)[0] > 127:
        gray = cv2.bitwise_not(gray)

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binarized = cv2.threshold(blurred, 0, 1, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # the kernel must have odd size, with an even one the anchor isn't in the middle
    # and OpenCV shifts the closed mask by 1 pixel right and down
    if closing_kernel_size % 2 == 0:
        closing_kernel_size += 1
    kernel = np.ones((closing_kernel_size, closing_kernel_size), np.uint8)
    return cv2.morphologyEx(binarized, cv2.MORPH_CLOSE, kernel)

def extract_fragments(
    original_image: np.ndarray,
    fragments_mask: np.ndarray
) -> list[ImageFragment]:
    """
    Converts a binary mask of fragments into a list of isolated ImageFragment objects.

    Args:
        original_image (np.ndarray): The source image array containing the fragments.
        fragments_mask (np.ndarray): A binary mask where 1 represents the fragments and 0 represents the background.

    Returns:
        list[ImageFragment]: A list of extracted image fragments with their bounding box data and alpha channels.
    """
    
    split_mask = (fragments_mask == 0).astype(np.uint8)
    return split_image(original_image, split_mask, EdgePixelAttributionOption.DISAPPEAR.value)

def border_median_colour(image: np.ndarray) -> list[int]:
    """
    Calculates the median color of the pixels located exactly on the outer edges of the image.

    Args:
        image (np.ndarray): The image array to analyze.

    Returns:
        list[int]: A list representing the median color values across all color channels.
    """

    pixels = image.reshape(image.shape[0], image.shape[1], -1)
    border = np.concatenate([pixels[0], pixels[-1], pixels[:, 0], pixels[:, -1]])
    return [int(v) for v in np.median(border, axis=0)]

def to_grayscale(image: np.ndarray) -> np.ndarray:
    """
    Converts a 2D, 3-channel, or 4-channel image to an 8-bit grayscale array.

    Args:
        image (np.ndarray): The source image array.

    Returns:
        np.ndarray: A 2D single-channel grayscale image array.
    """

    if image.ndim == 2:
        return image
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
