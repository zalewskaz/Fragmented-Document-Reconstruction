from models import ImageFragment, EdgePixelAttributionOption
import numpy as np
import cv2
import random

def split_image(
    original_image: np.ndarray,
    mask: np.ndarray,
    edge_pixel_option: str
) -> list[ImageFragment]:

    """
    Splits an image into individual fragments based on a provided split mask and resolves 
    border pixels according to a specified attribution strategy.

    Border pixels are either dropped entirely, assigned to one of the pieces they neighbor 
    randomly, or deterministically assigned to one of the pieces they neighbour so that all 
    pixels laying on a given edge get attributed to the same piece. 

    Each fragmented image is extracted into a cropped bounding box with a 5-pixel transparent 
    padding and an appended alpha channel.

    Args:
        original_image (np.ndarray): The source image array from which to extract pixel data.
        mask (np.ndarray):  A binary mask where 0 represents the interior of the fragments and 
                            1 represents the borders between fragments.
        edge_pixel_option (str):    The strategy for handling border pixels. Must match a valid 
                                    `EdgePixelAttributionOption` value.

    Returns:
        list[ImageFragment]:    A list of extracted image fragments. Each fragment contains padded 
                                image data with an alpha channel, along with its original x and y 
                                coordinates.

    Raises:
        ValueError: If an unknown `edge_pixel_option` is provided.
    """
    
    # invert the mask: fragments become 1 (foreground), borders become 0 (background) in order to be supported by cv2.connectedComponentsWithStats
    pieces_mask = (mask == 0).astype(np.uint8)

    # identify distinct pieces and fetch their bounding boxes
    # connectivity=4 so that diagonal pixels aren't grouped if separated by a border
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        pieces_mask,
        connectivity=4
    )

    # filter out noise (e.g. isolated pixels misclassified as pieces)
    valid_piece_ids = []
    for i in range(1, num_labels):
        if stats[i, cv2.CC_STAT_AREA] < 10:
            labels[labels == i] = 0
        else:
            valid_piece_ids.append(i)

    # save original labels to prevent border attribution from influencing subsequent neighbor detection
    original_piece_labels = labels.copy()

    # identify border pixels
    border_ys, border_xs = np.where(mask != 0)

    # apply the selected attribution strategy
    if edge_pixel_option == EdgePixelAttributionOption.DISAPPEAR.value:
        pass

    elif edge_pixel_option in (
        EdgePixelAttributionOption.RANDOM_ATTRIBUTION.value,
        EdgePixelAttributionOption.NON_RANDOM_ATTRIBUTION.value
    ):

        for y, x in zip(border_ys, border_xs):

            neighboring_labels = get_neighboring_piece_labels(
                y, x, original_piece_labels
            )

            # if edge pixel is only surrounded by edge pixels, get a label from these other edge pixels
            if not neighboring_labels:
                neighboring_labels = get_neighboring_piece_labels(
                    y, x, labels
                )

            if not neighboring_labels: 
                continue

            if edge_pixel_option == EdgePixelAttributionOption.RANDOM_ATTRIBUTION.value:
                selected_label = random.choice(list(neighboring_labels))

            else:
                selected_label = min(neighboring_labels)

            labels[y, x] = selected_label

    else:
        raise ValueError(
            f"Unknown edge pixel attribution option: {edge_pixel_option}"
        )

    # extract fragments
    fragments = []
    padding = 10
    channels = original_image.shape[2]

    for i in valid_piece_ids:

        ys, xs = np.where(labels == i)

        if len(ys) == 0:
            continue

        # Calculate bounding box
        x, y = xs.min(), ys.min()
        w = xs.max() - x + 1
        h = ys.max() - y + 1

        # extract the exact mask and image crop for this specific piece
        piece_label_mask = (labels[y:y+h, x:x+w] == i)
        piece_crop = original_image[y:y+h, x:x+w]

        pad_h, pad_w = h + 2 * padding, w + 2 * padding

        # initialize a zeroed (transparent) array with an alpha channel
        fragment_data = np.zeros(
            (pad_h, pad_w, channels),
            dtype=np.uint8
        )

        # view into the center of the padded array where the piece will go
        target_region = fragment_data[
            padding:padding+h,
            padding:padding+w
        ]

        # map original pixels to the target region using the boolean mask
        for ch in range(channels-1):
            target_region[piece_label_mask, ch] = (
                piece_crop[:, :, ch][piece_label_mask]
            )

        # set alpha channel to fully opaque for the piece pixels
        target_region[piece_label_mask, channels-1] = 255

        fragments.append(ImageFragment(
            data=fragment_data,
            original_x=x,
            original_y=y
        ))

    return fragments

def get_neighboring_piece_labels(
    y: int,
    x: int,
    labels: np.ndarray
) -> set[int]:
    """
    Identifies the unique IDs of all fragments adjacent to a given pixel.

    This function checks the 4-way neighborhood (top, bottom, left, right) of the 
    given coordinates within the label matrix. It ignores out-of-bounds coordinates 
    and background pixels (label 0).

    Args:
        y (int): The y-coordinate of the target pixel.
        x (int): The x-coordinate of the target pixel.
        labels (np.ndarray): A 2D array of integers where each value corresponds 
            to a distinct piece label (or 0 for background/unassigned).

    Returns:
        set[int]: A set containing the integer labels of all valid neighboring pieces.
    """

    h, w = labels.shape
    neighboring_labels = set()

    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        ny, nx = y + dy, x + dx

        if 0 <= ny < h and 0 <= nx < w:
            neighbor_label = labels[ny, nx]

            if neighbor_label != 0:
                neighboring_labels.add(neighbor_label)

    return neighboring_labels

def get_fragment_contours(original_image):
    height, width = original_image.shape[:2]
    mask = np.zeros((height, width), dtype=np.uint8)
    contour_mask = np.zeros((height, width), dtype=np.uint8)

    gray = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)

    corner_mean = gray[0:10, 0:10].mean()
    if corner_mean > 127:
        gray = cv2.bitwise_not(gray)

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # binarizing with Otsu
    _, binarized = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    k = np.ones((20, 20), np.uint8) 
    closed = cv2.morphologyEx(binarized, cv2.MORPH_CLOSE, k)

    contours, hierarchy = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    cv2.drawContours(mask, contours, -1, 1, cv2.FILLED)
    cv2.drawContours(contour_mask, contours, -1, 1, 1)

    return mask, contour_mask