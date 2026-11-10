from unittest.mock import Mock, patch
import cv2
import numpy as np
import pytest

from src.models import ImageFragment, EdgePixelAttributionOption
from src.processing import split_image, get_neighboring_piece_labels

# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------

# TODO: test also fragments that aren't rectangles 

@pytest.fixture
def sample_image():
    """Returns a 20x20 4-channel (BGR) image."""
    return np.ones((20, 20, 4), dtype=np.uint8) * 150

@pytest.fixture
def sample_mask():
    """
    Returns a 20x20 mask where 1 represents borders/background 
    and 0 represents piece interiors.
    Contains two distinct 5x5 pieces separated by borders.
    """
    mask = np.ones((20, 20), dtype=np.uint8)
    
    # Piece 1: area 25 (x: 2-6, y: 2-6)
    mask[2:7, 2:7] = 0 
    
    # Piece 2: area 25 (x: 10-14, y: 2-6)
    mask[2:7, 10:15] = 0
    
    return mask

@pytest.fixture
def small_noise_mask():
    """Returns a mask with a piece smaller than 10 pixels to test noise filtering."""
    mask = np.ones((20, 20), dtype=np.uint8)
    # Piece 1: area 9 (3x3), should be filtered out
    mask[2:5, 2:5] = 0 
    return mask


# ---------------------------------------------------------------------
# get_neighboring_piece_labels
# ---------------------------------------------------------------------

def test_get_neighboring_piece_labels_finds_all_directions():
    """Identify unique labels from top, bottom, left, and right."""
    labels = np.array([
        [0, 1, 0],
        [2, 9, 3],
        [0, 4, 0]
    ])
    
    result = get_neighboring_piece_labels(1, 1, labels)
    
    assert result == {1, 2, 3, 4}


def test_get_neighboring_piece_labels_ignores_background():
    """Ignore 0 (background) labels when collecting neighbors."""
    labels = np.array([
        [0, 0, 0],
        [0, 9, 2],
        [0, 0, 0]
    ])
    
    result = get_neighboring_piece_labels(1, 1, labels)
    
    assert result == {2}


def test_get_neighboring_piece_labels_handles_edges():
    """Do not raise index errors when the target pixel is on the image edge."""
    labels = np.array([
        [1, 2],
        [3, 4]
    ])
    
    # Top-left corner (0, 0) - neighbors are right (2) and down (3)
    result = get_neighboring_piece_labels(0, 0, labels)
    
    assert result == {2, 3}


def test_get_neighboring_piece_labels_returns_empty_when_isolated():
    """Return an empty set if surrounded entirely by background."""
    labels = np.array([
        [0, 0, 0],
        [0, 5, 0],
        [0, 0, 0]
    ])
    
    result = get_neighboring_piece_labels(1, 1, labels)
    
    assert result == set()


def test_get_neighboring_piece_labels_removes_duplicates():
    """Return labels with no duplicates."""
    labels = np.array([
        [0, 1, 0],
        [1, 5, 2],
        [0, 3, 0]
    ])
    
    result = get_neighboring_piece_labels(1, 1, labels)
    
    assert result == {1, 2, 3}

def test_get_neighboring_piece_labels_ignores_corner_neigbours():
    """Do not return labels of pieces cornering the main piece."""
    labels = np.array([
        [0, 1, 0],
        [1, 5, 2],
        [0, 3, 4]
    ])
    
    result = get_neighboring_piece_labels(1, 1, labels)
    
    assert result == {1, 2, 3}


# ---------------------------------------------------------------------
# split_image
# ---------------------------------------------------------------------

def test_split_image_rejects_unknown_attribution_option(sample_image, sample_mask):
    """Raise a ValueError if an invalid edge pixel option is passed."""
    with pytest.raises(ValueError, match="Unknown edge pixel attribution option"):
        split_image(sample_image, sample_mask, "INVALID_OPTION")


def test_split_image_filters_noise(sample_image, small_noise_mask):
    """Ignore connected components with an area smaller than 10 pixels."""
    fragments = split_image(
        sample_image, 
        small_noise_mask, 
        EdgePixelAttributionOption.DISAPPEAR.value
    )
    
    assert len(fragments) == 0


def test_split_image_extracts_correct_number_of_pieces(sample_image, sample_mask):
    """Return a fragment for each valid piece in the mask."""
    fragments = split_image(
        sample_image, 
        sample_mask, 
        EdgePixelAttributionOption.DISAPPEAR.value
    )
    
    assert len(fragments) == 2


def test_split_image_adds_padding_and_alpha_channel(sample_image, sample_mask):
    """Ensure output fragments have 10px padding and an alpha channel."""
    fragments = split_image(
        sample_image, 
        sample_mask, 
        EdgePixelAttributionOption.DISAPPEAR.value
    )
    
    fragment = fragments[0]
    # original piece is 5x5, so with 10px padding on all sides, it should be 25x25
    assert fragment.data.shape == (25, 25, 4)
    
    # original x and y should match the crop coordinates (2, 2) and (2, 10) - in any order
    assert fragment.original_y == 2
    assert fragment.original_x in [2, 10]


@patch("src.processing.image_splitter.random.choice")
def test_split_image_applies_random_attribution(mock_choice, sample_image):
    """Assign border pixels randomly based on neighboring piece labels."""
    # mock random.choice to always pick the highest label
    mock_choice.side_effect = lambda seq: max(seq)
    
    mask = np.ones((10, 10), dtype=np.uint8)
    mask[:, 2:4] = 0  # piece 1
    mask[:, 5:7] = 0  # piece 2
    
    fragments = split_image(
        sample_image,
        mask,
        EdgePixelAttributionOption.RANDOM_ATTRIBUTION.value
    )
    
    assert len(fragments) == 2
    mock_choice.assert_called()
    
    fragments_sorted = sorted(fragments, key=lambda f: f.original_x)
    piece_1 = fragments_sorted[0]
    piece_2 = fragments_sorted[1]
    
    assert piece_1.data.shape[1] == 23
    assert piece_2.data.shape[1] == 26


def test_split_image_applies_non_random_attribution(sample_image):
    """Assign border pixels deterministically to the lowest neighbor label."""
    mask = np.ones((10, 10), dtype=np.uint8)
    
    mask[:, 2:4] = 0  # piece 1
    mask[:, 5:7] = 0  # piece 2
        
    fragments = split_image(
        sample_image,
        mask,
        EdgePixelAttributionOption.NON_RANDOM_ATTRIBUTION.value
    )
    
    fragments_sorted = sorted(fragments, key=lambda f: f.original_x)
    piece_1 = fragments_sorted[0]
    piece_2 = fragments_sorted[1]
    
    assert piece_1.data.shape[1] == 24
    assert piece_2.data.shape[1] == 25


def test_split_image_handles_edge_pixels_with_only_edge_neighbors(sample_image):
    """Resolve edge pixels surrounded only by other edge pixels using the fallback."""
    mask = np.ones((10, 10), dtype=np.uint8)
    mask[2:7, 2:4] = 0  # piece 1 (x coords: 2-3)
    mask[2:7, 7:9] = 0  # piece 2 (x coords: 7-8)
    
    # border pixels at x = 4, 5, 6
    # x=4 should get piece 1, x=5 piece 1 (by fallback logic), x=6 piece 
    
    fragments = split_image(
        sample_image, 
        mask, 
        EdgePixelAttributionOption.NON_RANDOM_ATTRIBUTION.value
    )

    fragments_sorted = sorted(fragments, key=lambda f: f.original_x)

    piece_1 = fragments_sorted[0]
    piece_2 = fragments_sorted[1]

    assert piece_1.original_x == 1
    assert piece_1.data.shape == (29, 29, 4)