import numpy as np
import cv2
from models import ImageFragment

def count_left_blank_columns(cropped_data: np.ndarray, color_diff_threshold: int = 30) -> int:
    """
    Counts contiguous blank columns starting from the left edge.
    A column is blank if very few pixels differ significantly from the column's base color.
    """
    gray = cv2.cvtColor(cropped_data[:, :, :3], cv2.COLOR_BGR2GRAY)
    
    blank_count = 0
    h, w = gray.shape
    
    # allow up to 5% of the column's pixels to be dark spots (dust/noise)
    noise_tolerance = h * 0.05 
    
    for col_idx in range(w):
        col_data = gray[:, col_idx]
        
        # calculate the base background color of this specific column
        col_median = np.median(col_data)
        
        # count how many pixels differ from the base color to a large extent
        diff = np.abs(col_data.astype(np.int32) - int(col_median))
        outliers = np.count_nonzero(diff > color_diff_threshold)
        
        # if there are very few differing pixels, it's a blank column
        if outliers <= noise_tolerance:
            blank_count += 1
        else:
            break
            
    return blank_count

def reconstruct_unrotated_strips(fragments_list: list[ImageFragment]):
    # dont handle empty fragment list
    if not fragments_list:
        return None
    
    # 1. extract edge data for each fragment
    # for each fragment we extract (for each of 2 side borders) a chain of pixel brightnesses
    # save those into a list: fragment (object), left pixel chain, right pixel chain

    processed_fragments = []
    for fragment in fragments_list:
        data = fragment.data
        
        # extract the alpha channel to find the visible bounds
        alpha = data[:, :, 3]
        
        # find indices of columns that have at least one visible (non-transparent) pixel
        valid_cols = np.where(np.any(alpha > 0, axis=0))[0]
        if len(valid_cols) == 0:
            continue  # skip entirely transparent fragments
            
        left_col_idx = valid_cols[0]
        right_col_idx = valid_cols[-1]
        
        # crop the fragment data to remove transparent side padding
        cropped_data = data[:, left_col_idx:right_col_idx + 1, :]
        
        # extract left and right edge pixels (ignoring the alpha channel for matching)
        left_edge_bgr = cropped_data[:, 0, :3]
        right_edge_bgr = cropped_data[:, -1, :3]
        
        # convert the edges to chains of pixel brightness (grayscale)
        # reshape to (H, 1, 3) to use cv2.cvtColor, then flatten to a 1D float array
        left_chain = cv2.cvtColor(left_edge_bgr.reshape(-1, 1, 3), cv2.COLOR_BGR2GRAY).flatten().astype(np.float32)
        right_chain = cv2.cvtColor(right_edge_bgr.reshape(-1, 1, 3), cv2.COLOR_BGR2GRAY).flatten().astype(np.float32)

        # combine them into a dictionary with the fragment and cropped data
        processed_fragments.append({
            'fragment': fragment,
            'cropped_data': cropped_data,
            'left_chain': left_chain,
            'right_chain': right_chain
        })

    # 2. find the true left edge (most blank lines on the left)
    best_anchor_idx = 0
    max_blank_cols = -1

    for i, pf in enumerate(processed_fragments):
        # count how many contiguous background-color columns exist starting from the left edge
        blank_cols = count_left_blank_columns(pf['cropped_data']) 
        if blank_cols > max_blank_cols:
            max_blank_cols = blank_cols
            best_anchor_idx = i
    
    # 3. deciding which strips to connect with each other
    # placeholder (very weak algorithm): we take 1 piece, check match with every other piece, match it to the best one
    # repeat until all fragments are matched
    
    # we maintain a growing list of assembled pieces, starting with the first one,
    # and attach the best matching piece to its right side until all are used

    # start with the piece with most blank lines on the left
    assembled = [processed_fragments.pop(best_anchor_idx)]
    unmatched = processed_fragments

    while unmatched:
        best_match_score = float('inf')
        best_match_idx = -1
        attach_to_left = False
        
        # the exposed right edge of our currently assembled block
        assembled_edge = assembled[-1]['right_chain']
        
        for i, cand in enumerate(unmatched):
            cand_left = cand['left_chain']
            
            # score candidate's LEFT edge against the assembled RIGHT edge
            score = np.sum((cand_left - assembled_edge) ** 2)
            
            if score < best_match_score:
                best_match_score = score
                best_match_idx = i
                attach_to_left = False
                
        # remove the best candidate from unmatched and add it to our assembled list
        best_candidate = unmatched.pop(best_match_idx)
        
        if attach_to_left:
            assembled.insert(0, best_candidate)
        else:
            assembled.append(best_candidate)

    # 4. visually combine those into a full picture and return it (OpenCV BGRA format)
    # since they are vertical strips of equal height, we can horizontally stack the cropped data arrays
    images_to_combine = [item['cropped_data'] for item in assembled]
    reconstructed_image = np.hstack(images_to_combine)

    return reconstructed_image