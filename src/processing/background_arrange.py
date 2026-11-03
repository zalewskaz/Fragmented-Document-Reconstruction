import numpy as np
import random
import cv2
from models import ImageFragment

DARK_BACKGROUND = (64, 64, 64, 255)
LIGHT_BACKGROUND = (192, 192, 192, 255)


def pick_background_colour(image: np.ndarray) -> tuple[int, int, int, int]:
    """
    Picks a background colour that the pieces will stand out against.

    If the document is mostly light, we use a dark-gray background.
    If the document is mostly dark, we use a light-gray background.

    Works for grayscale, BGR and BGRA images.
    """
    if image.shape[2] == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    elif image.shape[2] == 4:
        gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    else:
        raise Exception("unsupported image format (neither BGR nor BGRA)")

    return DARK_BACKGROUND if gray.mean() > 127 else LIGHT_BACKGROUND


def arrange_on_background(height: int, width: int, fragments_list: list[ImageFragment],
                          bg_colour: tuple[int, int, int, int] = DARK_BACKGROUND) -> np.ndarray:
    bg_h = int(1.5 * height)
    bg_w = int(1.5 * width)
    max_attempts = 100
    
    # store tuples of (x, y, w, h, fragment)
    placed_pieces = []

    min_x = np.inf
    min_y = np.inf
    max_x = -1
    max_y = -1
    
    for frag in fragments_list:
        frag_h, frag_w = frag.data.shape[:2]
        
        placed_successfully = False
        while not placed_successfully:
            # if the piece is wider than the background, force an expansion
            if bg_w <= frag_w:
                bg_w += int(width * 0.25)
                continue
                
            for _ in range(max_attempts):
                # pick a random top-left corner
                rx = random.randint(0, bg_w - frag_w)
                ry = random.randint(0, bg_h - frag_h)
                
                # check for bounding box collisions with already placed pieces
                overlap = False
                for (px, py, pw, ph, _) in placed_pieces:
                    if not (rx + frag_w <= px or rx >= px + pw or ry + frag_h <= py or ry >= py + ph):
                        overlap = True
                        break
                
                if not overlap:
                    placed_pieces.append((rx, ry, frag_w, frag_h, frag))
                    placed_successfully = True
                    # update min/max x/y values
                    if rx < min_x: 
                        min_x = rx
                    if ry < min_y: 
                        min_y = ry
                    if rx + frag_w > max_x:
                        max_x = rx + frag_w
                    if ry + frag_h > max_y:
                        max_y = ry + frag_h
                    break
            
            # if we failed `max_attempts` times, expand the background height and width and try this piece again
            if not placed_successfully:
                bg_w += int(width * 0.25)
                bg_h += int(height * 0.25)
    
    # cut down unused background from all sides, leaving 5px padding so that pieces dont touch the edge
    offset_x = min_x - 5
    offset_y = min_y - 5
    bg_w = max_x - offset_x + 5
    bg_h = max_y - offset_y + 5
    
    # rendering phase
    # fill the whole background with the chosen colour
    background = np.full((bg_h, bg_w, 4), bg_colour, dtype=np.uint8)
    
    for x, y, w, h, frag in placed_pieces:
        roi = background[y-offset_y:y-offset_y+h, x-offset_x:x-offset_x+w]
        
        piece_data = frag.data
        channels = piece_data.shape[2]
        
        # normalize 2-channel (Grayscale+Alpha) to 4-channel (BGRA+Alpha) to match background
        if channels == 2:
            gray, alpha = piece_data[..., 0], piece_data[..., 1]
            piece_bgra = np.empty((h, w, 4), dtype=np.uint8)
            piece_bgra[..., 0] = gray
            piece_bgra[..., 1] = gray
            piece_bgra[..., 2] = gray
            piece_bgra[..., 3] = alpha
        else:
            piece_bgra = piece_data
            
        # create a boolean mask of the piece's non-transparent pixels
        alpha_mask = piece_bgra[..., -1] > 0
        
        # overwrite only the non-transparent pixels in the region of interest
        roi[alpha_mask] = piece_bgra[alpha_mask]
        
    return background