import numpy as np
import pytest

from src.models.fragment import ImageFragment
from src.processing import fragment_rotation as fr

# TODO: test also fragments that aren't rectangles 
def make_fragment(height, width, colour=(10, 120, 230), rotation=0.0, patterned=False):
    """
    Creates a fragment like the ones from image_splitter: a rectangular piece
    of the given height and width, filled with one colour, with a 5 px transparent margin on each side.
    With patterned=True every pixel gets a different colour
    """
    data = np.zeros((height + 2 * fr.PADDING, width + 2 * fr.PADDING, 4), dtype=np.uint8)

    if patterned:
        rng = np.random.default_rng(0)
        colour = rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)

    data[fr.PADDING:fr.PADDING + height, fr.PADDING:fr.PADDING + width, :3] = colour
    data[fr.PADDING:fr.PADDING + height, fr.PADDING:fr.PADDING + width, 3] = 255
    return ImageFragment(data=data, original_x=7, original_y=13, rotation=rotation)


# --------------------------------------------
# rotate_fragment
# --------------------------------------------

def test_rotate_fragment_by_0_keeps_data():
    fragment = make_fragment(20, 30, patterned=True)

    rotated = fr.rotate_fragment(fragment, 0)

    assert np.array_equal(rotated.data, fragment.data), "Rotation by 0 degrees shouldn't change the fragment"

@pytest.mark.parametrize("angle, k", [(90, 1), (180, 2), (270, 3)])
def test_rotate_fragment_right_angles_match_numpy(angle, k):
    fragment = make_fragment(20, 30, patterned=True)

    rotated = fr.rotate_fragment(fragment, angle)
    expected = np.rot90(fragment.data, k)
    assert rotated.data.shape == expected.shape, f"Expected shape {expected.shape}, got {rotated.data.shape}"
    assert np.array_equal(rotated.data, expected), f"Rotation by {angle} degrees moved pixels to wrong places"

def test_rotate_fragment_keeps_position_and_updates_rotation():
    fragment = make_fragment(20, 30, rotation=300)

    rotated = fr.rotate_fragment(fragment, 90)

    assert rotated.original_x == fragment.original_x, "original_x shouldn't change"
    assert rotated.original_y == fragment.original_y, "original_y shouldn't change"
    assert rotated.rotation == 30, f"Rotation should be (300 + 90) % 360 = 30, got {rotated.rotation}"

def test_rotate_fragment_doesnt_change_original():
    fragment = make_fragment(20, 30, patterned=True)
    data_before = fragment.data.copy()

    fr.rotate_fragment(fragment, 45)

    assert np.array_equal(fragment.data, data_before), "Original fragment data shouldn't be modified"
    assert fragment.rotation == 0, "Original fragment rotation shouldn't be modified"

@pytest.mark.parametrize("angle", [1, 17, 45, 89.5, 123.5, 300])
def test_rotate_fragment_any_angle_keeps_colour_and_margin(angle):
    colour = (10, 120, 230)
    fragment = make_fragment(40, 60, colour=colour)

    rotated = fr.rotate_fragment(fragment, angle)
    data = rotated.data
    alpha = data[..., 3]

    # every pixel is either fully transparent or a fully opaque part of the piece
    assert set(np.unique(alpha)) <= {0, 255}, "Alpha should only contain 0 and 255"

    # edges aren't darkened by blending with the transparent background
    piece_colours = data[alpha == 255][:, :3]
    assert np.all(np.abs(piece_colours.astype(int) - colour) <= 1), "Piece colour changed after rotation"

    # 5 px transparent margin on each side, and the piece touches it on every side
    assert np.all(alpha[:fr.PADDING] == 0) and np.all(alpha[-fr.PADDING:] == 0), "Top/bottom margin isn't transparent"
    assert np.all(alpha[:, :fr.PADDING] == 0) and np.all(alpha[:, -fr.PADDING:] == 0), "Left/right margin isn't transparent"
    assert np.any(alpha[fr.PADDING]) and np.any(alpha[-fr.PADDING - 1]), "Piece should be trimmed to the margin (top/bottom)"
    assert np.any(alpha[:, fr.PADDING]) and np.any(alpha[:, -fr.PADDING - 1]), "Piece should be trimmed to the margin (left/right)"

    # rotating changes only a few edge pixels, not a big part of the piece
    area_before = np.count_nonzero(fragment.data[..., 3])
    area_after = np.count_nonzero(alpha)
    assert abs(area_after - area_before) / area_before < 0.05, (
        f"Piece area changed too much: {area_before} -> {area_after}"
    )


@pytest.mark.parametrize("angle", [30, 135, 250, 300])
def test_rotate_fragment_any_angle_moves_content_to_right_place(angle):
    fragment = make_fragment(40, 60)

    # red marker in the top left corner of the piece
    marker_colour = (0, 0, 255)
    fragment.data[fr.PADDING:fr.PADDING + 10, fr.PADDING:fr.PADDING + 10, :3] = marker_colour

    rotated = fr.rotate_fragment(fragment, angle)

    def marker_offset(data):
        """Position of the marker's centre relative to the piece's centre (x, y)."""
        piece_ys, piece_xs = np.nonzero(data[..., 3])
        marker_ys, marker_xs = np.nonzero((data[..., 3] == 255) & (data[..., 1] < 60))
        return np.array([marker_xs.mean() - piece_xs.mean(), marker_ys.mean() - piece_ys.mean()])

    rad = np.radians(angle)
    rotation_matrix = np.array([
        [np.cos(rad), np.sin(rad)],
        [-np.sin(rad), np.cos(rad)],
    ])
    expected = rotation_matrix @ marker_offset(fragment.data)
    actual = marker_offset(rotated.data)

    assert np.allclose(actual, expected, atol=1.5), (
        f"Marker should be at {expected.round(1)} from the piece centre, got {actual.round(1)} "
        "- the piece was rotated in the wrong direction or mirrored"
    )

def test_rotate_fragment_too_small_piece_returns_original():
    # 1 px piece rotated by 45 degrees isn't at least half covering any pixel, so nothing is left
    fragment = make_fragment(1, 1, rotation=10)

    rotated = fr.rotate_fragment(fragment, 45)

    assert np.array_equal(rotated.data, fragment.data), "Original data should be returned"
    assert rotated.rotation == fragment.rotation, "Rotation shouldn't change when the piece wasn't rotated"
    assert rotated.original_x == fragment.original_x, "original_x shouldn't change"
    assert rotated.original_y == fragment.original_y, "original_y shouldn't change"


# --------------------------------------------
# rotate_fragments_randomly / 90deg / 180deg
# --------------------------------------------

@pytest.mark.parametrize("rotate_all, allowed_angles", [
    (fr.rotate_fragments_90deg, {0, 90, 180, 270}),
    (fr.rotate_fragments_180deg, {0, 180}),
])
def test_rotate_fragments_uses_allowed_angles(rotate_all, allowed_angles):
    fragments = [make_fragment(20, 30) for _ in range(20)]

    rotated = rotate_all(fragments)

    assert len(rotated) == len(fragments), "Every fragment should be rotated"
    angles = {f.rotation for f in rotated}
    assert angles <= allowed_angles, f"Expected angles from {allowed_angles}, got {angles}"
    assert len(angles) > 1, f"Angles should be random, but all fragments got {angles}"

def test_rotate_fragments_randomly_uses_angles_in_range():
    fragments = [make_fragment(20, 30) for _ in range(20)]

    rotated = fr.rotate_fragments_randomly(fragments)

    assert len(rotated) == len(fragments), "Every fragment should be rotated"
    assert all(0 <= f.rotation < 360 for f in rotated), "Angles should be between 0 and 360 degrees"
    angles = {f.rotation for f in rotated}
    assert len(angles) > 1, f"Angles should be random, but all fragments got {angles}"

def test_rotate_fragments_empty_list():
    assert fr.rotate_fragments_randomly([]) == []
    assert fr.rotate_fragments_90deg([]) == []
    assert fr.rotate_fragments_180deg([]) == []
