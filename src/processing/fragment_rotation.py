import math
import random
import numpy as np
import cv2
from models import ImageFragment

PADDING = 5


def rotate_fragment(fragment: ImageFragment, angle: float) -> ImageFragment:
    """
    Rotates an image fragment by a specified angle counter-clockwise.

    Args:
        fragment (ImageFragment): The original image fragment to be rotated.
        angle (float): The rotation angle in degrees (counter-clockwise).

    Returns:
        ImageFragment: A new ImageFragment instance containing the rotated image 
        data with 5px transparent padding on each side, along with updated rotation 
        metadata.
    """

    data = fragment.data
    h, w = data.shape[:2]
    channels = data.shape[2]

    # how big the canvas has to be for the rotated piece to fit
    rad = math.radians(angle)
    cos, sin = abs(math.cos(rad)), abs(math.sin(rad))
    # we round before ceil because cos(90°) isn't exactly 0 in floats - without it the canvas
    # would get one extra pixel and the piece would end up shifted by half a pixel (and blurry)
    new_w = int(math.ceil(round(w * cos + h * sin, 6)))
    new_h = int(math.ceil(round(w * sin + h * cos, 6)))

    # rotate around the middle of the piece and move it so it sits in the middle of the bigger canvas
    matrix = cv2.getRotationMatrix2D(((w - 1) / 2, (h - 1) / 2), angle, 1.0)
    matrix[0, 2] += (new_w - w) / 2
    matrix[1, 2] += (new_h - h) / 2

    # transparent pixels are black (0), so when the edges get blended during rotation they'd turn darker;
    # dividing the colour by the blended alpha afterwards brings the edge pixels back to their real colour
    rotated = cv2.warpAffine(
        data.astype(np.float32), matrix, (new_w, new_h),
        flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0,
    )
    if rotated.ndim == 2:  # cv2 drops the last dimension when there's only one channel, so we add it back
        rotated = rotated[..., np.newaxis]

    alpha = rotated[..., -1]
    colour = rotated[..., :-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        colour = np.where(alpha[..., None] > 0, colour * 255.0 / alpha[..., None], 0)

    # after blending, alpha on the edges is somewhere between 0 and 255 -
    # we count a pixel as part of the piece if it's at least half covered
    piece_mask = alpha >= 127.5

    result = np.zeros((new_h, new_w, channels), dtype=np.uint8)
    result[..., :-1][piece_mask] = np.clip(np.round(colour[piece_mask]), 0, 255).astype(np.uint8)
    result[..., -1][piece_mask] = 255

    # trim the empty space around the piece and add the 5 px margin back
    ys, xs = np.nonzero(piece_mask)
    if len(ys) == 0:  # the piece was so tiny that nothing was left after rotating - just keep the original
        return ImageFragment(data=data, original_x=fragment.original_x, original_y=fragment.original_y,
                             rotation=fragment.rotation)

    cropped = result[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    padded = np.zeros((cropped.shape[0] + 2 * PADDING, cropped.shape[1] + 2 * PADDING, channels), dtype=np.uint8)
    padded[PADDING:PADDING + cropped.shape[0], PADDING:PADDING + cropped.shape[1]] = cropped

    return ImageFragment(
        data=padded,
        original_x=fragment.original_x,
        original_y=fragment.original_y,
        rotation=(fragment.rotation + angle) % 360,
    )


def rotate_fragments_randomly(fragments_list: list[ImageFragment]) -> list[ImageFragment]:
    """Applies a continuous random rotation to a collection of image fragments.

    Args:
        fragments_list (list[ImageFragment]): The list of fragments to rotate.

    Returns:
        list[ImageFragment]: A new list of fragments, each independently rotated 
        by a random angle between 0.0 and 360.0 degrees."""
    return [rotate_fragment(frag, random.uniform(0, 360)) for frag in fragments_list]

def rotate_fragments_90deg(fragments_list: list[ImageFragment]) -> list[ImageFragment]:
    """
    Applies a random orthogonal rotation to a collection of image fragments.

    Args:
        fragments_list (list[ImageFragment]): The list of fragments to rotate.

    Returns:
        list[ImageFragment]: A new list of fragments, each independently rotated 
        by a randomly chosen angle of 0, 90, 180, or 270 degrees.
    """
    return [rotate_fragment(frag, random.choice([0, 90, 180, 270])) for frag in fragments_list]

def rotate_fragments_180deg(fragments_list: list[ImageFragment]) -> list[ImageFragment]:
    """
    Applies a random flip-like rotation to a collection of image fragments.

    Args:
        fragments_list (list[ImageFragment]): The list of fragments to rotate.

    Returns:
        list[ImageFragment]: A new list of fragments, each independently rotated 
        by a randomly chosen angle of either 0 or 180 degrees.
    """
    return [rotate_fragment(frag, random.choice([0, 180])) for frag in fragments_list]