from models import ImageFragment
import numpy as np  
import cv2

def split_image(original_image: np.ndarray, mask: np.ndarray) -> list[ImageFragment]:
    # TODO: add other splitting methods (jagged edges rather than missing pixels)

    # invert the mask: fragments become 1 (foreground), borders become 0 (background) in order to be supported by cv2.connectedComponentsWithStats
    pieces_mask = (mask == 0).astype(np.uint8)
    
    # identify distinct pieces and fetch their bounding boxes
    # connectivity=4 so that diagonal pixels aren't grouped if separated by a border
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(pieces_mask, connectivity=4)
    
    fragments = []
    padding = 5
    channels = original_image.shape[2] # save into height*width*4 bgra array

    # label 0 is the background (the borders), so we iterate from 1 to num_labels
    for i in range(1, num_labels):
        x, y, w, h, area = stats[i]
        
        # filter out noise (e.g. isolated pixels misclassified as pieces)
        if area < 10:
            continue
            
        # extract the exact mask and image crop for this specific piece
        piece_label_mask = (labels[y:y+h, x:x+w] == i)
        piece_crop = original_image[y:y+h, x:x+w]
        
        pad_h, pad_w = h + 2 * padding, w + 2 * padding
        
        # initialize a zeroed (transparent) array with an alpha channel
        output_channels = channels + 1 
        fragment_data = np.zeros((pad_h, pad_w, output_channels), dtype=np.uint8)
        
        # view into the center of the padded array where the piece will go
        target_region = fragment_data[padding:padding+h, padding:padding+w]
        
        # map original pixels to the target region using the boolean mask
        for ch in range(channels):
            target_region[piece_label_mask, ch] = piece_crop[:, :, ch][piece_label_mask]
        # set alpha channel to fully opaque for the piece pixels
        target_region[piece_label_mask, channels] = 255
            
        fragments.append(ImageFragment(
            data=fragment_data, 
            original_x=x, 
            original_y=y
        ))
        
    return fragments