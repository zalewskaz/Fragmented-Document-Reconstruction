import numpy as np
import random
from models import ImageFragment

def arrange_on_background(height: int, width: int, fragments_list: list[ImageFragment]) -> np.ndarray:
    # TODO: switch background colour depending on whether the image is light or dark
    
    bg_h = int(1.5 * height)
    bg_w = width
    max_attempts = 100
    
    # store tuples of (x, y, w, h, fragment)
    placed_pieces = []
    
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
                    break
            
            # if we failed `max_attempts` times, expand the background width and try this piece again
            if not placed_successfully:
                bg_w += int(width * 0.25)
    
    # rendering phase
    # initialize a dark-gray background (BGRA format: 64, 64, 64, 255)
    background = np.full((bg_h, bg_w, 4), [64, 64, 64, 255], dtype=np.uint8)
    
    for x, y, w, h, frag in placed_pieces:
        roi = background[y:y+h, x:x+w]
        
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