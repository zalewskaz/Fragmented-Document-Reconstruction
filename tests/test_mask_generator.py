import cv2
import numpy as np
import pytest
from unittest.mock import MagicMock

from src.models.parameters_enums import SplittingMethod
from src.processing import mask_generator as mg

# --------------------------------------------
# random_normal_ints
# --------------------------------------------

def test_random_normal_ints_shape_and_type():
    low, high, size = 1, 10, 5
    
    result = mg.random_normal_ints(low, high, size=size)
    
    assert isinstance(result, np.ndarray), "Return object different than a numpy array"
    assert result.shape == (size,), f"Expected size ({size},), got {result.shape}"
    assert np.issubdtype(result.dtype, np.integer), "Values should be integers"

@pytest.mark.parametrize("low, high, size", [
    (0, 10, 100), 
    (-50, -10, 50),
    (5, 5, 10),
])
def test_random_normal_ints_respects_bounds(low, high, size):
    result = mg.random_normal_ints(low, high, size=size)
    
    assert np.all(result >= low), f"Found values below {low}"
    assert np.all(result <= high), f"Found values over {high}"


# --------------------------------------------
# random_cuts
# --------------------------------------------

def test_random_cuts_correct_amount_of_cuts():
    val = 1000 # width of a document
    max_strips = 10
    strips_n = 4 # expected 3 cuts
    
    cut_points = mg.random_cuts(val, max_strips, strips_n)
    
    assert isinstance(cut_points, np.ndarray), "Return object different than a numpy array"
    assert len(cut_points) == strips_n - 1, "Number of cuts should be one less than the number of strips"

def test_random_cuts_respects_max_strips():
    val = 1000
    max_strips = 5
    strips_n = 20
    
    cut_points = mg.random_cuts(val, max_strips, strips_n)
    
    assert len(cut_points) == max_strips - 1, "Function didn't block the amount of strips to max_strips"

def test_random_cuts_handles_none_strips_n():
    val = 1000
    max_strips = 6
    strips_n = None # random number of strips
    
    cut_points = mg.random_cuts(val, max_strips, strips_n)
    
    assert isinstance(cut_points, np.ndarray), "Return object different than a numpy array"
    assert len(cut_points) < max_strips, "Random number of cuts shouldn't exceed max_strips - 1"

def test_random_cuts_logic_and_bounds():
    val = 500
    max_strips = 10
    strips_n = 5
    
    cut_points = mg.random_cuts(val, max_strips, strips_n)
    
    assert np.all(np.diff(cut_points) > 0), "Cuts should be in ascending order"
    assert np.all(cut_points > 0), "Cut points shouldn't be smaller than 0"
    assert np.all(cut_points < val), f"Cut points shouldn't exceed the document width ({val})"


# --------------------------------------------
# even_vertical_mask
# --------------------------------------------

def test_even_vertical_mask_only_width_given():
    height, width = 200, 100
    mask = np.zeros((height, width), dtype=np.uint8)
    strips_width = 30
    
    new_mask = mg.even_vertical_mask(mask, width, strips_n=None, strips_width=strips_width)

    assert isinstance(mask, np.ndarray), "Mask should be a numpy array"
    assert np.all(new_mask[:, 30] == 1), "Expected a cut at column 30"
    assert np.all(new_mask[:, 60] == 1), "Expected a cut at column 60"

def test_even_vertical_mask_only_n_given():
    height, width = 200, 100
    mask = np.zeros((height, width), dtype=np.uint8)
    strips_n = 5

    new_mask = mg.even_vertical_mask(mask, width, strips_n=strips_n, strips_width=None)

    assert isinstance(mask, np.ndarray), "Mask should be a numpy array"

    number_of_cuts = np.sum(new_mask[0, :])
    assert number_of_cuts == strips_n - 1, f"Expected {strips_n - 1} cuts, got {number_of_cuts}"
    
    for cut_col in [20, 40, 60, 80]:
        assert np.all(new_mask[:, cut_col] == 1), f"Expected a solid cut line at column {cut_col}"

def test_even_vertical_mask_min_fragment_limit():
    height, width = 100, 100
    mask = np.zeros((height, width), dtype=np.uint8)
    
    strips_width = width - mg.MIN_FRAGMENT_WIDTH + 5
    
    new_mask = mg.even_vertical_mask(mask, width, strips_n=None, strips_width=strips_width)

    assert isinstance(mask, np.ndarray), "Mask should be a numpy array"
    assert np.all(new_mask == 0), "Mask should be empty; cut was made too close to the right edge"


# --------------------------------------------
# random_vertical_mask
# --------------------------------------------

def test_random_vertical_mask_draws_full_lines():
    height, width = 100, 200
    mask = np.zeros((height, width), dtype=np.uint8)
    strips_n = 4
    
    new_mask = mg.random_vertical_mask(mask, width, strips_n)

    number_of_cuts = np.sum(new_mask[0, :])
    assert number_of_cuts == strips_n - 1, f"Expected {strips_n - 1} cut lines, got {number_of_cuts}"

    cut_indices = np.where(new_mask[0, :] == 1)[0]
    for col_idx in cut_indices:
        assert np.all(new_mask[:, col_idx] == 1), f"Cut line at column {col_idx} is not drawn fully from top to bottom"

def test_random_vertical_mask_too_small_width():
    height, width = 50, mg.MIN_FRAGMENT_WIDTH-5 
    mask = np.zeros((height, width), dtype=np.uint8)
    strips_n = 3
    
    new_mask = mg.random_vertical_mask(mask, width, strips_n)

    assert np.all(new_mask == 0), "Mask should remain completely empty when width is too small"

def test_random_vertical_mask_caps_at_max_strips():
    height, width = 100, 1000 
    mask = np.zeros((height, width), dtype=np.uint8)

    strips_n = 50 
    
    new_mask = mg.random_vertical_mask(mask, width, strips_n)

    number_of_cuts = np.sum(new_mask[0, :])
    assert number_of_cuts <= 19, f"Expected maximum of 19 cuts due to limit, but got {number_of_cuts}"


# --------------------------------------------
# even_horizontal_mask
# --------------------------------------------

def test_even_horizontal_mask_only_height_given():
    height, width = 200, 100
    mask = np.zeros((height, width), dtype=np.uint8)
    strips_height = 60
    
    new_mask = mg.even_horizontal_mask(mask, height, strips_n=None, strips_height=strips_height)

    assert isinstance(mask, np.ndarray), "Mask should be a numpy array"
    assert np.all(new_mask[60, :] == 1), "Expected a cut at row 60"
    assert np.all(new_mask[120, :] == 1), "Expected a cut at row 120"

def test_even_horizontal_mask_only_n_given():
    height, width = 200, 100
    mask = np.zeros((height, width), dtype=np.uint8)
    strips_n = 5

    new_mask = mg.even_horizontal_mask(mask, height, strips_n=strips_n, strips_height=None)

    assert isinstance(mask, np.ndarray), "Mask should be a numpy array"

    number_of_cuts = np.sum(new_mask[:, 0])
    assert number_of_cuts == strips_n - 1, f"Expected {strips_n - 1} cuts, got {number_of_cuts}"
    
    for cut_row in [40, 80, 120, 160]:
        assert np.all(new_mask[cut_row, :] == 1), f"Expected a solid cut line at column {cut_row}"

def test_even_horizontal_mask_min_fragment_limit():
    height, width = 100, 100
    mask = np.zeros((height, width), dtype=np.uint8)
    
    strips_height = height - mg.MIN_FRAGMENT_WIDTH + 5
    
    new_mask = mg.even_horizontal_mask(mask, height, strips_n=None, strips_height=strips_height)

    assert isinstance(mask, np.ndarray), "Mask should be a numpy array"
    assert np.all(new_mask == 0), "Mask should be empty; cut was made too close to the right edge"


# --------------------------------------------
# random_horizontal_mask
# --------------------------------------------

def test_random_horizontal_mask_draws_full_lines():
    height, width = 200, 100
    mask = np.zeros((height, width), dtype=np.uint8)
    strips_n = 4
    
    new_mask = mg.random_horizontal_mask(mask, height, strips_n)

    number_of_cuts = np.sum(new_mask[:, 0])
    assert number_of_cuts == strips_n - 1, f"Expected {strips_n - 1} cut lines, got {number_of_cuts}"

    cut_indices = np.where(new_mask[:, 0] == 1)[0]
    for row_idx in cut_indices:
        assert np.all(new_mask[row_idx, :] == 1), f"Cut line at column {row_idx} is not drawn fully from left to right"

def test_random_horizontal_mask_too_small_height():
    height, width = mg.MIN_FRAGMENT_WIDTH-5, 50
    mask = np.zeros((height, width), dtype=np.uint8)
    strips_n = 3
    
    new_mask = mg.random_horizontal_mask(mask, height, strips_n)

    assert np.all(new_mask == 0), "Mask should remain completely empty when height is too small"

def test_random_horizontal_mask_caps_at_max_strips():
    height, width = 1000, 100 
    mask = np.zeros((height, width), dtype=np.uint8)

    strips_n = 50 
    
    new_mask = mg.random_horizontal_mask(mask, height, strips_n)

    number_of_cuts = np.sum(new_mask[:, 0])
    assert number_of_cuts <= 24, f"Expected maximum of 24 cuts due to limit, but got {number_of_cuts}"    


# --------------------------------------------
# segmented_mask
# --------------------------------------------

def test_segmented_mask_even_width_and_equal_segments():
    height, width = 300, 300
    mask = np.zeros((height, width), dtype=np.uint8)
    v_strips = 3
    h_strips = 4
    
    new_mask = mg.segmented_mask(
        mask, height, width, 
        strips_vertical_n=v_strips, 
        strips_horizontal_n=h_strips, 
        equal_segments=True, 
        even_width=True
    )

    assert isinstance(new_mask, np.ndarray), "Mask should be a numpy array"
    assert np.all(new_mask[:, 100] == 1), "Expected a full vertical cut at column 100"
    assert np.all(new_mask[:, 200] == 1), "Expected a full vertical cut at column 200"
    
    horizontal_sums = np.sum(new_mask, axis=1)
    assert np.max(horizontal_sums) < width, "Horizontal cuts should not span the entire width of the image"

    expected_h_cuts = h_strips - 1
    
    for mid_col in [50, 150, 250]:
        cuts_in_segment = np.sum(new_mask[:, mid_col])
        assert cuts_in_segment == expected_h_cuts, (
            f"Expected {expected_h_cuts} horizontal cuts in segment around column {mid_col}, "
            f"but got {cuts_in_segment}"
        )

def test_segmented_mask_random_and_none_handling():
    height, width = 400, 400
    mask = np.zeros((height, width), dtype=np.uint8)
    
    new_mask = mg.segmented_mask(
        mask, height, width, 
        strips_vertical_n=None, 
        strips_horizontal_n=None, 
        equal_segments=False, 
        even_width=False
    )

    assert isinstance(new_mask, np.ndarray), "Mask should be a numpy array"
    assert np.any(new_mask == 1), "Mask should not be empty; cuts should be generated"
    assert set(np.unique(new_mask)).issubset({0, 1}), "Mask should only contain 0 and 1"

def test_segmented_mask_skips_all_if_size_too_small():
    height, width = mg.MIN_FRAGMENT_WIDTH-5, mg.MIN_FRAGMENT_WIDTH-5
    mask = np.zeros((height, width), dtype=np.uint8)
    
    new_mask = mg.segmented_mask(
        mask, height, width, 
        strips_vertical_n=5, 
        strips_horizontal_n=5, 
        equal_segments=True, 
        even_width=True
    )

    assert np.all(new_mask == 0), "Mask should remain empty if size is too small for cuts"


# --------------------------------------------
# get_random_point_on_edge
# --------------------------------------------

@pytest.mark.parametrize("edge, check_x_bound, check_y_bound, fixed_x, fixed_y", [
    (0, True, False, None, 0),
    (1, False, True, 99, None),
    (2, True, False, None, 199),
    (3, False, True, 0, None),
])
def test_get_random_point_on_edge_bounds(edge, check_x_bound, check_y_bound, fixed_x, fixed_y):
    width, height = 100, 200
    
    x, y = mg.get_random_point_on_edge(edge, width, height)
    
    assert isinstance(x, int) and isinstance(y, int), "Coordinates must be integers"
    
    if fixed_x is not None:
        assert x == fixed_x, f"For edge {edge}, expected x to be exactly {fixed_x}, got {x}"
    if fixed_y is not None:
        assert y == fixed_y, f"For edge {edge}, expected y to be exactly {fixed_y}, got {y}"
        
    if check_x_bound:
        assert 0 <= x < width, f"x coordinate {x} is out of bounds for width {width}"
    if check_y_bound:
        assert 0 <= y < height, f"y coordinate {y} is out of bounds for height {height}"


# --------------------------------------------
# is_cut_valid
# --------------------------------------------

def test_is_cut_valid_all_fragments_large_enough():
    height, width = 100, 100
    mask = np.zeros((height, width), dtype=np.uint8)
    
    mask[:, 50] = 1
    
    is_valid = mg.is_cut_valid(mask)
    
    assert is_valid is True, "Cut should be valid as all fragments are larger than MIN_FRAGMENT_AREA"

def test_is_cut_valid_with_too_small_fragment():
    height, width = 100, 100
    mask = np.zeros((height, width), dtype=np.uint8)
    
    # this cut should create a too small fragment
    mask[:, 3] = 1
    
    is_valid = mg.is_cut_valid(mask)
    
    assert is_valid is False, "Cut should be invalid as one fragment is smaller than MIN_FRAGMENT_AREA"


# --------------------------------------------
# hierarchical_random_lines_mask
# --------------------------------------------

def test_hierarchical_random_lines_mask_success():
    height, width = 500, 500
    mask = np.zeros((height, width), dtype=np.uint8)
    lines_n = 3
    mock_warning = MagicMock()
    
    new_mask = mg.hierarchical_random_lines_mask(mask, height, width, lines_n, warning_callback=mock_warning)
    
    assert isinstance(new_mask, np.ndarray), "Mask should be a numpy array"
    assert np.any(new_mask == 1), "Mask should contain cuts (1s) after successful generation"

    # no callback should be called if the space is big enough for 3 lines
    mock_warning.assert_not_called()

def test_hierarchical_random_lines_mask_single_cut_properties():
    height, width = 100, 100
    mask = np.zeros((height, width), dtype=np.uint8)
    lines_n = 1
    
    new_mask = mg.hierarchical_random_lines_mask(mask, height, width, lines_n, warning_callback=None)
    
    unique_vals = np.unique(new_mask)
    assert np.all(np.isin(unique_vals, [0, 1])), "Mask should only contain 0 and 1"
    
    line_pixels = np.sum(new_mask)
    assert line_pixels >= 40, (
        f"Line length {line_pixels} is too short. "
        "A valid cut resulting in fragments >= MIN_FRAGMENT_AREA must be at least ~40 pixels long."
    )

def test_hierarchical_random_lines_mask_stops_when_largest_piece_too_small():
    height, width = 30, 20
    mask = np.zeros((height, width), dtype=np.uint8)
    
    mock_warning = MagicMock()
    
    new_mask = mg.hierarchical_random_lines_mask(mask, height, width, lines_n=3, warning_callback=mock_warning)
    
    assert np.all(new_mask == 0), "Mask should remain empty if the largest piece is < MIN_FRAGMENT_AREA * 2"

    # callback should be called if the space isn't big enough
    assert mock_warning.call_count == 1, "Warning callback should be called exactly once when limit is exceeded"


# --------------------------------------------
# get_bezier_curve
# --------------------------------------------

def test_get_bezier_curve_shape_and_type():
    points = np.array([[10, 10], [50, 90], [90, 10]])
    num_points = 50
    
    curve = mg.get_bezier_curve(points, num_points=num_points)
    
    assert isinstance(curve, np.ndarray), "Curve must be a numpy array"
    assert curve.shape == (num_points, 2), f"Expected shape ({num_points}, 2), got {curve.shape}"
    assert curve.dtype == np.int32, "Curve coordinates must be 32-bit integers"

def test_get_bezier_curve_endpoints():
    start_pt = [0, 0]
    end_pt = [100, 100]
    points = np.array([start_pt, [20, 80], [80, 20], end_pt])
    
    curve = mg.get_bezier_curve(points, num_points=100)
    
    assert np.array_equal(curve[0], start_pt), f"Curve should start at {start_pt}, but started at {curve[0]}"
    assert np.array_equal(curve[-1], end_pt), f"Curve should end at {end_pt}, but ended at {curve[-1]}"


# --------------------------------------------
# polylines_mask
# --------------------------------------------

def test_polylines_mask_straight_success():
    height, width = 300, 300
    mask = np.zeros((height, width), dtype=np.uint8)
    mock_warning = MagicMock()
    
    new_mask = mg.polylines_mask(mask, height, width, lines_n=2, points_k=2, warning_callback=mock_warning, bezier=False)
    
    assert isinstance(new_mask, np.ndarray), "Mask should be a numpy array"
    assert np.any(new_mask == 1), "Mask should contain polyline cuts"
    mock_warning.assert_not_called()

def test_polylines_mask_bezier_success():
    height, width = 300, 300
    mask = np.zeros((height, width), dtype=np.uint8)
    mock_warning = MagicMock()
    
    new_mask = mg.polylines_mask(mask, height, width, lines_n=2, points_k=3, warning_callback=mock_warning, bezier=True)
    
    assert isinstance(new_mask, np.ndarray), "Mask should be a numpy array"
    assert np.any(new_mask == 1), "Mask should contain Bezier curve cuts"
    mock_warning.assert_not_called()

def test_polylines_mask_too_small_triggers_warning():
    height, width = 30, 30
    mask = np.zeros((height, width), dtype=np.uint8)
    mock_warning = MagicMock()
    
    new_mask = mg.polylines_mask(mask, height, width, lines_n=5, points_k=1, warning_callback=mock_warning)
    
    # callback should be called if the space isn't big enough
    mock_warning.assert_called_once()
    warning_message = mock_warning.call_args[0][0]
    assert "Time limit exceeded" in warning_message, "Callback should inform about exceeded attempts"


# --------------------------------------------
# voronoi_mask
# --------------------------------------------

def test_voronoi_mask_success():
    height, width = 400, 400
    mask = np.zeros((height, width), dtype=np.uint8)
    mock_warning = MagicMock()
    
    new_mask = mg.voronoi_mask(mask, height, width, points_n=5, warning_callback=mock_warning)
    
    assert isinstance(new_mask, np.ndarray), "Mask should be a numpy array"
    assert np.any(new_mask == 1), "Mask should contain Voronoi facets"
    mock_warning.assert_not_called()

def test_voronoi_mask_fails_min_dist_requirement():
    height, width = 40, 40
    mask = np.zeros((height, width), dtype=np.uint8)
    mock_warning = MagicMock()
    points_n = 3
    
    new_mask = mg.voronoi_mask(mask, height, width, points_n=points_n, warning_callback=mock_warning)
    
    # callback should be called if we expect too many points (min points distance is 50)
    mock_warning.assert_called_once()
    
    warning_message = mock_warning.call_args[0][0]
    assert "Time limit exceeded" in warning_message, "Callback should inform about exceeded time limit due to min_dist"
    assert f"out of {points_n} centers used" in warning_message, "Message should contain correct expected centers count"

def test_voronoi_mask_correct_number_of_polygons():
    height, width = 400, 400
    mask = np.zeros((height, width), dtype=np.uint8)
    points_n = 4
    
    new_mask = mg.voronoi_mask(mask, height, width, points_n, warning_callback=None)
    
    assert np.any(new_mask == 1), "Voronoi facets should be drawn"
    
    inverse_mask = np.where(new_mask == 0, 255, 0).astype(np.uint8)
    num_labels, _, _, _ = cv2.connectedComponentsWithStats(inverse_mask, connectivity=4)
    number_of_fragments = num_labels - 1
    
    assert number_of_fragments == points_n, (
        f"Expected exactly {points_n} closed polygons for {points_n} centers, "
        f"but got {number_of_fragments} fragments. Lines might not be fully closed."
    )


# --------------------------------------------
# generate_mask
# --------------------------------------------

@pytest.mark.parametrize("method, height, width, kwargs", [
    # EVEN VERTICAL
    (SplittingMethod.EVEN_VERTICAL, 200, 200, {"strips_vertical_n": 5}),
    (SplittingMethod.EVEN_VERTICAL, 200, 200, {"strips_vertical_n": 25}),
    (SplittingMethod.EVEN_VERTICAL, 300, 400, {"strips_width": 50}),
    (SplittingMethod.EVEN_VERTICAL, 300, 400, {"strips_width": 120}),

    # EVEN HORIZONTAL
    (SplittingMethod.EVEN_HORIZONTAL, 400, 200, {"strips_horizontal_n": 18}),
    (SplittingMethod.EVEN_HORIZONTAL, 200, 200, {"strips_height": 40}),
    (SplittingMethod.EVEN_HORIZONTAL, 300, 200, {"strips_height": 60}),
    (SplittingMethod.EVEN_HORIZONTAL, 400, 200, {"strips_height": 80}),

    # RANDOM VERTICAL & HORIZONTAL
    (SplittingMethod.RANDOM_VERTICAL, 200, 500, {"strips_vertical_n": 4}),
    (SplittingMethod.RANDOM_HORIZONTAL, 500, 200, {"strips_horizontal_n": 6}),
    (SplittingMethod.RANDOM_VERTICAL, 20, 50, {"strips_vertical_n": 4}),
    (SplittingMethod.RANDOM_HORIZONTAL, 50, 20, {"strips_horizontal_n": 6}),

    # RECTANGLES
    (SplittingMethod.EVEN_RECTANGLES, 300, 300, {"strips_vertical_n": 3, "strips_horizontal_n": 3}),
    (SplittingMethod.EVEN_RECTANGLES, 300, 300, {"strips_vertical_n": 5, "strips_horizontal_n": 13}),
    (SplittingMethod.RANDOM_RECTANGLES, 400, 400, {"strips_vertical_n": 4, "strips_horizontal_n": 4}),
    (SplittingMethod.RANDOM_RECTANGLES, 400, 400, {"strips_vertical_n": 10, "strips_horizontal_n": 1}),

    # SEGMENTED STRIPS
    (SplittingMethod.SEGMENTED_STRIPS, 300, 300, {"strips_vertical_n": 3, "strips_horizontal_n": 3, "equal_segments": True}),
    (SplittingMethod.SEGMENTED_STRIPS, 300, 300, {"strips_vertical_n": 10, "strips_horizontal_n": 5, "equal_segments": True, "even_width": False}),
    (SplittingMethod.SEGMENTED_STRIPS, 400, 400, {"strips_vertical_n": 4, "equal_segments": False, "even_width": False}),

    # POLYLINES & CURVES
    (SplittingMethod.STRAIGHT_POLYGONS, 300, 300, {"lines_n": 4, "hierarchical": False}),
    (SplittingMethod.STRAIGHT_POLYGONS, 300, 300, {"lines_n": 4, "hierarchical": True}),
    (SplittingMethod.STRAIGHT_POLYGONS, 300, 300, {"lines_n": 8, "hierarchical": False}),
    (SplittingMethod.STRAIGHT_POLYGONS, 300, 300, {"lines_n": 8, "hierarchical": True}),
    (SplittingMethod.POLYLINE_POLYGONS, 300, 300, {"lines_n": 3, "points_k": 4}),
    (SplittingMethod.POLYLINE_POLYGONS, 400, 400, {"lines_n": 5, "points_k": 2}),
    (SplittingMethod.BEZIER_CURVES, 300, 300, {"lines_n": 4, "points_k": 3}),

    # VORONOI
    (SplittingMethod.VORONOI_POLYGONS, 400, 400, {"points_n": 5}),
    (SplittingMethod.VORONOI_POLYGONS, 500, 500, {"points_n": 15}),
])

def test_generate_mask_integration(method, height, width, kwargs):
    mask = mg.generate_mask(
        splitting_method=method, 
        height=height, 
        width=width, 
        **kwargs
    )
    
    assert isinstance(mask, np.ndarray), "Mask should be a numpy array"
    assert mask.shape == (height, width), f"Expected shape {(height, width)}, got {mask.shape}"
    unique_values = np.unique(mask)
    assert np.all(np.isin(unique_values, [0, 1])), "Mask should only contain 0s and 1s"
    
    assert np.any(mask == 1), f"Mask generated by {method.name} is completely empty"
    
    assert mg.is_cut_valid(mask) is True, f"Method {method.name} generated fragments smaller than MIN_FRAGMENT_AREA"