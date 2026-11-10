import numpy as np
import pytest

from src.models.fragment import ImageFragment
from src.processing import background_arrange as ba


# TODO: test also fragments that aren't rectangles
def make_fragment(height, width, colour=(10, 120, 230)):
    """
    Creates a fragment like the ones from image_splitter: a rectangular piece
    of the given height and width, filled with one colour, with a 5 px transparent margin on each side.
    """
    data = np.zeros((height + 10, width + 10, 4), dtype=np.uint8)
    data[5:5 + height, 5:5 + width, :3] = colour
    data[5:5 + height, 5:5 + width, 3] = 255
    return ImageFragment(data=data, original_x=0, original_y=0)


def count_colour(image, colour):
    """
    Counts the pixels of the given colour in an image.

    In the tests every fragment has its own colour, so this tells how much of
    a fragment is visible in the result.
    """
    return np.count_nonzero(np.all(image[..., :3] == colour, axis=-1))


# --------------------------------------------
# pick_background_colour
# --------------------------------------------

@pytest.mark.parametrize("value, expected", [
    (255, ba.DARK_BACKGROUND),   # white document -> dark background
    (200, ba.DARK_BACKGROUND),
    (50, ba.LIGHT_BACKGROUND),   # dark document -> light background
    (0, ba.LIGHT_BACKGROUND),
])
def test_pick_background_colour_contrasts_with_document(value, expected):
    image = np.full((10, 10, 3), value, dtype=np.uint8)

    assert ba.pick_background_colour(image) == expected

def test_pick_background_colour_threshold():
    # the background is dark only when the mean brightness is above 127
    assert ba.pick_background_colour(np.full((10, 10, 3), 127, dtype=np.uint8)) == ba.LIGHT_BACKGROUND
    assert ba.pick_background_colour(np.full((10, 10, 3), 128, dtype=np.uint8)) == ba.DARK_BACKGROUND

def test_pick_background_colour_unsupported_format():
    image = np.zeros((10, 10, 2), dtype=np.uint8)

    with pytest.raises(Exception, match="unsupported image format"):
        ba.pick_background_colour(image)


# --------------------------------------------
# arrange_on_background
# --------------------------------------------

def test_arrange_on_background_output_format():
    fragments = [make_fragment(20, 30) for _ in range(3)]

    result = ba.arrange_on_background(100, 100, fragments)

    assert isinstance(result, np.ndarray), "Result should be a numpy array"
    assert result.dtype == np.uint8, "Result should be of type uint8"
    assert result.ndim == 3 and result.shape[2] == 4, "Result should be a BGRA image"

def test_arrange_on_background_all_pieces_visible_and_not_overlapping():
    # every piece has its own colour, so we can count each one separately
    colours = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (0, 255, 255)]
    fragments = [make_fragment(20, 30, colour) for colour in colours]

    result = ba.arrange_on_background(100, 100, fragments)

    # if pieces overlapped, some pixels of one colour would be covered by another
    for colour in colours:
        visible = count_colour(result, colour)
        assert visible == 20 * 30, f"Piece {colour} should have {20 * 30} visible pixels, got {visible}"

def test_arrange_on_background_uses_given_colour():
    fragments = [make_fragment(20, 30)]

    result = ba.arrange_on_background(100, 100, fragments, bg_colour=ba.LIGHT_BACKGROUND)

    piece_pixels = 20 * 30
    background_pixels = count_colour(result, ba.LIGHT_BACKGROUND[:3])
    assert background_pixels == result.shape[0] * result.shape[1] - piece_pixels, (
        "Every pixel outside the piece should have the background colour"
    )
    assert np.all(result[..., 3] == 255), "The result shouldn't have transparent pixels"

def test_arrange_on_background_transparent_margin_shows_background():
    fragments = [make_fragment(20, 30)]

    result = ba.arrange_on_background(100, 100, fragments)

    # the background is cropped to the piece with its 5 px transparent margin, plus 5 px of padding,
    # so there are 10 px of background around the piece
    assert result.shape[:2] == (20 + 20, 30 + 20), f"Expected shape (40, 50), got {result.shape[:2]}"
    border = np.ones(result.shape[:2], dtype=bool)
    border[10:-10, 10:-10] = False
    assert np.all(result[border, :3] == ba.DARK_BACKGROUND[:3]), "The 10 px border should be background"

def test_arrange_on_background_expands_when_pieces_dont_fit():
    # 12 pieces as big as the original image can't fit on a 1.5x bigger background
    colours = [(i * 20, 255 - i * 20, 100) for i in range(12)]
    fragments = [make_fragment(50, 50, colour) for colour in colours]

    result = ba.arrange_on_background(50, 50, fragments)

    for colour in colours:
        assert count_colour(result, colour) == 50 * 50, f"Piece {colour} is missing or covered"

def test_arrange_on_background_piece_wider_than_background():
    # a piece wider than 1.5x the original width (e.g. a rotated piece)
    fragments = [make_fragment(20, 200)]

    result = ba.arrange_on_background(100, 100, fragments)

    assert count_colour(result, (10, 120, 230)) == 20 * 200, "The whole piece should be visible"

def test_arrange_on_background_piece_taller_than_background():
    # e.g. a horizontal strip of a wide document, rotated by 90 degrees
    fragments = [make_fragment(200, 20)]

    result = ba.arrange_on_background(100, 100, fragments)

    assert count_colour(result, (10, 120, 230)) == 200 * 20, "The whole piece should be visible"

def test_arrange_on_background_empty_list():
    result = ba.arrange_on_background(100, 100, [])

    assert result.shape == (150, 150, 4), "With no pieces the result should be the empty 1.5x background"
    assert np.all(result == ba.DARK_BACKGROUND), "The whole result should be background"
