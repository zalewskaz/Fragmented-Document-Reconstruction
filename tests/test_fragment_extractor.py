import pytest
import numpy as np
import cv2
from unittest.mock import patch, MagicMock

from src.models import ExtractionMethod, EdgePixelAttributionOption
from src.processing import get_fragment_contours, extract_fragments, flood_fill_foreground, otsu_foreground, border_median_colour, to_grayscale, split_image

# --------------------------------------------
# border_median_colour
# --------------------------------------------

def test_border_median_colour_grayscale():
    img = np.zeros((10, 10), dtype=np.uint8)
    
    # A frame with 100s on the borders
    img[0, :] = 100
    img[-1, :] = 100
    img[:, 0] = 100
    img[:, -1] = 100
    
    # Noise on the corner
    img[0, 0] = 50
    
    # Differently colored inside
    img[2:8, 2:8] = 200 
    
    result = border_median_colour(img)
    
    assert result == [100], "The median should ignore the inside and noise values."

def test_border_median_colour_bgr():
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    
    # A blue frame
    border_color = [255, 0, 0]
    img[0, :] = border_color
    img[-1, :] = border_color
    img[:, 0] = border_color
    img[:, -1] = border_color
    
    # Red inside
    img[2:8, 2:8] = [0, 0, 255] 
    
    result = border_median_colour(img)
    
    assert result == [255, 0, 0], "The median should be blue."


# --------------------------------------------
# to_grayscale
# --------------------------------------------

def test_to_grayscale_already_2d():
    img = np.zeros((10, 10), dtype=np.uint8)
    result = to_grayscale(img)
    
    assert result.ndim == 2, "Return array with more or less than 2 dimensions."
    assert result.shape == (10, 10), "Return array with a different shape than the input array."
    assert np.array_equal(result, img), "Function changed an already grayscaled imaged."

def test_to_grayscale_from_bgr():
    img = np.full((10, 10, 3), 255, dtype=np.uint8)
    result = to_grayscale(img)
    
    assert result.ndim == 2, "Return array with more or less than 2 dimensions."
    assert result.shape == (10, 10), "Return array with a different shape than the input array."
    assert result[0, 0] == 255, "Return array values different than white."

def test_to_grayscale_from_bgra():
    img = np.full((10, 10, 4), 128, dtype=np.uint8)
    result = to_grayscale(img)
    
    assert result.ndim == 2, "Return array with more or less than 2 dimensions."
    assert result.shape == (10, 10), "Return array with a different shape than the input array."


# --------------------------------------------
# extract_fragments
# --------------------------------------------

def test_extract_fragments():
    original_img = np.zeros((15, 15, 4), dtype=np.uint8)
    fragments_mask = np.zeros((15, 15), dtype=np.uint8)
    
    fragments_mask[5:10, 5:10] = 1 
    
    result = extract_fragments(original_img, fragments_mask)
    
    assert isinstance(result, list), "The result should be a list."
    
    assert len(result) == 1, f"Should have found exactly 1 fragment, found {len(result)}"
    
    assert result[0].data.shape == (25, 25, 4), "Fragment has no added padding."


# --------------------------------------------
# flood_fill_foreground
# --------------------------------------------

def test_flood_fill_foreground_bgr():
    # 50x50 black image (background)
    img = np.zeros((50, 50, 3), dtype=np.uint8)
    
    # White square in the middle (fragment)
    img[15:35, 15:35] = [255, 255, 255]
    
    result = flood_fill_foreground(img, tolerance=10)
    
    assert result.shape == (50, 50), "Resulting mask shape should match original image height and width"
    assert result.dtype == np.uint8, "Mask should be of type uint8"
    
    assert result[25, 25] == 1, "Pixels inside the fragment should be marked as 1"
    
    assert result[5, 5] == 0, "Pixels in the background should be marked as 0"
    
    assert np.all(result[15:35, 15:35] == 1), "The entire fragment area should be 1"
    assert np.all(result[0:10, :] == 0), "The top background area should be strictly 0"

def test_flood_fill_foreground_grayscale():
    img = np.full((50, 50), 100, dtype=np.uint8) # Gray background
    img[20:30, 20:30] = 200 # Lighter gray fragment
    
    result = flood_fill_foreground(img, tolerance=10)
    
    assert result.ndim == 2, "Result should be a 2D array"
    assert result[25, 25] == 1, "Fragment interior should be correctly isolated as 1"
    assert result[0, 0] == 0, "Background should be flooded and set to 0"


# --------------------------------------------
# otsu_foreground
# --------------------------------------------

def test_otsu_foreground_dark_background():
    img = np.zeros((100, 100, 3), dtype=np.uint8) # Dark background
    img[30:70, 30:70] = [200, 200, 200] # Bright fragment
    
    result = otsu_foreground(img, closing_kernel_size=5)
    
    assert result.shape == (100, 100), "Resulting mask should have the same dimensions as input"
    assert result[50, 50] == 1, "The bright center fragment should be detected and marked as 1"
    assert result[5, 5] == 0, "The dark background should be marked as 0"

def test_otsu_foreground_light_background():
    img = np.full((100, 100, 3), 240, dtype=np.uint8) # White background
    img[30:70, 30:70] = [20, 20, 20] # Dark fragment
    
    result = otsu_foreground(img, closing_kernel_size=5)
    
    assert result[50, 50] == 1, "The dark fragment on a light background should be inverted and marked as 1"
    assert result[5, 5] == 0, "The light background should be recognized and marked as 0"

def test_otsu_foreground_even_kernel_size():
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[40:60, 40:60] = [255, 255, 255]
    
    # even kernel size
    result = otsu_foreground(img, closing_kernel_size=4)
    
    assert result.shape == (100, 100), "Execution should succeed and return the correct shape even with an even kernel size"
    assert result[50, 50] == 1, "Fragment should still be properly extracted"

# --------------------------------------------
# get_fragment_contours
# --------------------------------------------

def test_get_fragment_contours_flood_fill():
    # an image with a single large square fragment
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[20:80, 20:80] = [255, 255, 255] 
    
    frag_mask, contour_mask = get_fragment_contours(
        original_image=img,
        method=ExtractionMethod.FLOOD_FILL.value,
        min_fragment_area=100
    )
    
    # Check shapes and types
    assert frag_mask.shape == (100, 100), "Fragment mask shape must match the original image"
    assert contour_mask.shape == (100, 100), "Contour mask shape must match the original image"
    assert frag_mask.dtype == np.uint8, "Fragment mask must be of type uint8"
    
    # Check fragment mask
    assert frag_mask[50, 50] == 1, "The center of the fragment should be filled with 1 in the fragment mask"
    assert frag_mask[10, 10] == 0, "The background should be 0 in the fragment mask"
    
    # Check contour mask
    assert contour_mask[50, 50] == 0, "The center of the fragment should be empty (0) in the contour mask"
    assert contour_mask[10, 10] == 0, "The background should be empty (0) in the contour mask"
    assert np.any(contour_mask[19:22, 50] == 1), "The edge of the fragment should be marked as 1 in the contour mask"


def test_get_fragment_contours_otsu():
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[30:70, 30:70] = [200, 200, 200]
    
    frag_mask, _ = get_fragment_contours(
        original_image=img,
        method=ExtractionMethod.OTSU.value,
        min_fragment_area=100
    )
    
    assert frag_mask[50, 50] == 1, "The fragment should be properly extracted using the Otsu method"
    assert frag_mask[5, 5] == 0, "The background should be 0"


def test_get_fragment_contours_filters_small_areas():
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # large valid fragment
    img[10:60, 10:60] = [255, 255, 255]
    
    # small noise fragment
    img[80:84, 80:84] = [255, 255, 255]
    
    frag_mask, _ = get_fragment_contours(
        original_image=img,
        method=ExtractionMethod.FLOOD_FILL.value,
        min_fragment_area=100 # Threshold set high enough to ignore the 4x4 square
    )
    
    assert frag_mask[35, 35] == 1, "The large fragment should be kept and marked as 1"
    assert np.all(frag_mask[80:84, 80:84] == 0), "The small fragment should be filtered out and remain 0"