import cv2
import numpy as np
import pytest

from src.models import ImageFragment
from src.processing import (
    rotate_fragment, straighten_fragment, straighten_fragments, is_rectangle, arrange_in_rows
)

def make_fragment(height: int, width: int, padding: int = 10) -> ImageFragment:
    """A grey opaque rectangle height x width with a transparent margin, like an extracted fragment."""
    data = np.zeros((height + 2 * padding, width + 2 * padding, 4), dtype=np.uint8)
    data[padding:padding + height, padding:padding + width] = (200, 200, 200, 255)
    return ImageFragment(data=data, original_x=0, original_y=0)

def make_triangle() -> ImageFragment:
    data = np.zeros((140, 140, 4), dtype=np.uint8)
    triangle = np.array([[10, 10], [130, 10], [10, 130]], dtype=np.int32)
    cv2.fillPoly(data, [triangle], (200, 200, 200, 255))
    return ImageFragment(data=data, original_x=0, original_y=0)

def make_l_shape() -> ImageFragment:
    """A 100 x 100 square with a 50 x 50 corner cut out - it fills 75% of its rectangle."""
    fragment = make_fragment(100, 100)
    fragment.data[10:60, 60:110] = 0
    return fragment

def contour_and_rect(fragment: ImageFragment):
    contour = cv2.findContours((fragment.data[..., 3] > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0][0]
    return contour, cv2.minAreaRect(contour)

def opaque_bbox(fragment: ImageFragment) -> tuple[int, int, float]:
    """(height, width) of the opaque area's bounding box and how much of the box is filled."""
    ys, xs = np.nonzero(fragment.data[..., 3] > 0)
    height, width = ys.max() - ys.min() + 1, xs.max() - xs.min() + 1
    return height, width, len(ys) / (height * width)

@pytest.fixture
def rectangle():
    return make_fragment(60, 160)

# ---------------------------------------------------------------------
# straighten_fragment
# ---------------------------------------------------------------------

@pytest.mark.parametrize("angle", [10, 37, -20, 80, 100, 133, 200, 315, 45])
def test_rotated_rectangle_gets_axis_aligned(rectangle, angle):
    rotated = rotate_fragment(rectangle, angle)

    straightened, is_rect = straighten_fragment(rotated)

    assert is_rect
    height, width, filled = opaque_bbox(straightened)
    # the sides are axis-aligned, so the piece fills its bounding box (up to blurred corners)
    assert filled > 0.97
    # straightened up to a multiple of 90 degrees - the sides may be swapped
    assert sorted((height, width)) == pytest.approx([60, 160], abs=3)

def test_already_straight_rectangle_is_unchanged(rectangle):
    straightened, is_rect = straighten_fragment(rectangle)

    assert is_rect
    assert straightened is rectangle

def test_triangle_is_not_a_rectangle_and_stays_unchanged():
    triangle = make_triangle()

    result, is_rect = straighten_fragment(triangle)

    assert not is_rect
    assert result is triangle

def test_l_shape_is_not_a_rectangle():
    _, is_rect = straighten_fragment(rotate_fragment(make_l_shape(), 30))

    assert not is_rect

def test_rectangle_with_notch_still_counts_as_a_rectangle():
    notched = make_fragment(60, 160)
    notched.data[10:30, 80:95] = 0    # a 20 px deep notch from the top edge, e.g. left by the extraction

    straightened, is_rect = straighten_fragment(rotate_fragment(notched, 25))

    # it fills 97% of its rectangle - a damaged rectangle, straightened like any other
    assert is_rect
    height, width, _ = opaque_bbox(straightened)
    assert sorted((height, width)) == pytest.approx([60, 160], abs=3)

def test_rectangle_with_rounded_corners_counts_as_a_rectangle():
    # like the ones the brightness threshold extraction makes
    rounded = make_fragment(80, 160)
    rounded.data[...] = 0
    cv2.rectangle(rounded.data, (22, 10), (157, 89), (200, 200, 200, 255), thickness=-1)
    cv2.rectangle(rounded.data, (10, 22), (169, 77), (200, 200, 200, 255), thickness=-1)
    for x, y in [(22, 22), (157, 22), (22, 77), (157, 77)]:
        cv2.circle(rounded.data, (x, y), 12, (200, 200, 200, 255), thickness=-1)

    _, is_rect = straighten_fragment(rotate_fragment(rounded, 20))

    assert is_rect

def test_single_missing_pixels_on_the_edge_still_a_rectangle():
    damaged = make_fragment(60, 160)
    # a few pixels missing on the edge, like the ones the extraction sometimes leaves
    damaged.data[10:16, 50] = 0

    _, is_rect = straighten_fragment(rotate_fragment(damaged, 20))

    assert is_rect

def test_fully_transparent_fragment():
    empty = ImageFragment(data=np.zeros((20, 20, 4), dtype=np.uint8), original_x=0, original_y=0)

    result, is_rect = straighten_fragment(empty)

    assert result is empty
    assert not is_rect

def test_rotation_is_recorded(rectangle):
    straightened, _ = straighten_fragment(rotate_fragment(rectangle, 30))

    # rotated by 30 and straightened by the smallest angle: the total is a multiple of 90
    remainder = straightened.rotation % 90
    assert min(remainder, 90 - remainder) < 1

# ---------------------------------------------------------------------
# is_rectangle
# ---------------------------------------------------------------------

def test_is_rectangle():
    assert is_rectangle(*contour_and_rect(make_fragment(60, 160)))
    assert not is_rectangle(*contour_and_rect(make_triangle()))
    assert not is_rectangle(*contour_and_rect(make_l_shape()))

# ---------------------------------------------------------------------
# straighten_fragments
# ---------------------------------------------------------------------

def test_straighten_fragments_keeps_order_and_flags(rectangle):
    fragments = [rotate_fragment(rectangle, 25), make_triangle(), rectangle]

    results = straighten_fragments(fragments)

    assert [is_rect for _, is_rect in results] == [True, False, True]
    assert results[1][0] is fragments[1]

def test_straighten_fragments_stops(rectangle):
    calls = []

    def stop_after_one():
        calls.append(1)
        return len(calls) > 1

    results = straighten_fragments([rectangle, rectangle, rectangle], stop_callback=stop_after_one)

    assert len(results) == 1

# ---------------------------------------------------------------------
# arrange_in_rows
# ---------------------------------------------------------------------

def test_arrange_in_rows_places_every_fragment_without_overlap():
    fragments = [make_fragment(h, w) for h, w in [(60, 160), (100, 40), (30, 30), (80, 120), (50, 200)]]

    image, positions = arrange_in_rows(fragments, gap=10)

    assert len(positions) == len(fragments)
    for i, (x1, y1, w1, h1) in enumerate(positions):
        assert x1 >= 0 and y1 >= 0 and x1 + w1 <= image.shape[1] and y1 + h1 <= image.shape[0]
        for x2, y2, w2, h2 in positions[i + 1:]:
            assert x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1

    # the fragments' pixels are copied to their places
    x, y, w, h = positions[0]
    assert np.array_equal(image[y:y + h, x:x + w][fragments[0].data[..., 3] > 0],
                          fragments[0].data[fragments[0].data[..., 3] > 0])

def test_arrange_in_rows_empty():
    image, positions = arrange_in_rows([])

    assert positions == []
    assert image.ndim == 3 and image.shape[2] == 4
