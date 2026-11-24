# [Wall Painting Reconstruction Using a Genetic Algorithm](https://dl.acm.org/doi/epdf/10.1145/3084547)

import numpy as np
import random
from tqdm import tqdm
import math
import copy
import cv2
from processing import orient_fragments, straighten_fragments

class FitnessEvaluator:
    def __init__(self, fragments, contour_anchors, width, height, scale_factor=4.0, 
                 w_overlap=1200.0, w_out=2500.0, w_compact=2.5, w_edge_len=60.0, 
                 w_color_diff=1.5, w_cycle=6000.0, w_ink_match=300.0):
        self.fragments = fragments
        self.contour_anchors = contour_anchors
        self.scale_factor = scale_factor # speeds-up the calculations by resolution reduction
        
        self.orig_width = width
        self.orig_height = height
        self.width = int(width / scale_factor)
        self.height = int(height / scale_factor)
        
        self.w_overlap = w_overlap
        self.w_out = w_out
        self.w_compact = w_compact
        self.w_edge_len = w_edge_len
        self.w_color_diff = w_color_diff
        self.w_cycle = w_cycle
        self.w_ink_match = w_ink_match   # Bonus when dark ink/table lines continue across the seam
        
        self.kernel = np.ones((5, 5), np.uint8)

        # extracting binarized and grayscaled masks from the scaled fragments
        self.scaled_masks = []
        self.scaled_grays = []
        
        for frag in fragments:
            alpha = frag.data[:, :, 3]
            binary_mask = (alpha > 127).astype(np.uint8)
            gray_img = cv2.cvtColor(frag.data[:, :, :3], cv2.COLOR_BGR2GRAY)
            
            new_size = (max(1, int(binary_mask.shape[1] / scale_factor)), 
                        max(1, int(binary_mask.shape[0] / scale_factor)))
            
            scaled_mask = cv2.resize(binary_mask, new_size, interpolation=cv2.INTER_NEAREST)
            scaled_gray = cv2.resize(gray_img, new_size, interpolation=cv2.INTER_AREA)
            
            self.scaled_masks.append(scaled_mask)
            self.scaled_grays.append(scaled_gray)

    def _rotate_array(self, arr: np.ndarray, angle: float) -> np.ndarray:
        """
        Rotates the array by the given angle around the center to get bigger dimensions so that
        no fragment corner gets cut.
        """
        h, w = arr.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        cos_val = np.abs(M[0, 0])
        sin_val = np.abs(M[0, 1])
        new_w = int((h * sin_val) + (w * cos_val))
        new_h = int((h * cos_val) + (w * sin_val))
        
        M[0, 2] += (new_w / 2) - center[0]
        M[1, 2] += (new_h / 2) - center[1]

        # cv2.INTER_NEAREST interpolation so as not to blur the sharp edges of the binary mask
        return cv2.warpAffine(arr, M, (new_w, new_h), flags=cv2.INTER_NEAREST)

    def evaluate_with_graph(self, chromosome):
        """
        Evaluates a chromosome and also returns the set of touching fragment pairs
        (used by Jaccard diversity filtering in selection).
        """

        # changing the tree representation into fragment coordinates and rotation
        layout = decode_path_to_layout(
            chromosome=chromosome,
            fragments=self.fragments,
            contour_anchors=self.contour_anchors,
            board_width=self.orig_width,
            board_height=self.orig_height
        )

        # board counting how many fragments in a pixel
        board = np.zeros((self.height, self.width), dtype=np.int16)
        # bitmask board of outer borders to identify exact touching pairs (supports up to 63 fragments)
        border_id_board = np.zeros((self.height, self.width), dtype=np.uint64)
        
        seam_color_sum = np.zeros((self.height, self.width), dtype=np.float32)
        seam_color_sq_sum = np.zeros((self.height, self.width), dtype=np.float32)
        seam_count = np.zeros((self.height, self.width), dtype=np.int16)
        
        out_of_bounds_pixels = 0
        num_frags = len(layout)
        
        for i, gene in enumerate(layout):
            orig_x, orig_y, rot = gene
            mask = self.scaled_masks[i]
            gray = self.scaled_grays[i]

            # rotates the fragment            
            rotated_mask = self._rotate_array(mask, rot)
            rotated_gray = self._rotate_array(gray, rot)
            new_h, new_w = rotated_mask.shape
            
            start_x = int(orig_x / self.scale_factor)
            start_y = int(orig_y / self.scale_factor)
            
            b_x1, b_y1 = max(0, start_x), max(0, start_y)
            b_x2, b_y2 = min(self.width, start_x + new_w), min(self.height, start_y + new_h)

            # calculates pixels out of the bounds of our given paper
            if b_x1 >= b_x2 or b_y1 >= b_y2:
                out_of_bounds_pixels += int(np.sum(rotated_mask))
                continue
                
            m_x1 = b_x1 - start_x
            m_y1 = b_y1 - start_y
            m_x2 = m_x1 + (b_x2 - b_x1)
            m_y2 = m_y1 + (b_y2 - b_y1)
            
            valid_mask = rotated_mask[m_y1:m_y2, m_x1:m_x2]
            valid_gray = rotated_gray[m_y1:m_y2, m_x1:m_x2].astype(np.float32)

            # dialtion to find the outer border of the fragment
            dilated = cv2.dilate(valid_mask, self.kernel, iterations=1)
            outer_border = dilated - valid_mask

            # propagating the edge color for that outer border
            masked_gray = np.where(valid_mask == 1, valid_gray, 0.0)
            propagated_gray = cv2.dilate(masked_gray, self.kernel, iterations=1)

            # saving info for counting fragments in pixel, identifying touching pairs and counting brightness on edges
            if b_x1 < b_x2 and b_y1 < b_y2:
                board[b_y1:b_y2, b_x1:b_x2] += valid_mask
                
                border_bool = (outer_border == 1)
                bit_flag = np.uint64(1) << np.uint64(i % 63)
                border_id_board[b_y1:b_y2, b_x1:b_x2][border_bool] |= bit_flag
                
                seam_color_sum[b_y1:b_y2, b_x1:b_x2][border_bool] += propagated_gray[border_bool]
                seam_color_sq_sum[b_y1:b_y2, b_x1:b_x2][border_bool] += (propagated_gray[border_bool] ** 2)
                seam_count[b_y1:b_y2, b_x1:b_x2][border_bool] += 1
                
            pixels_on_board = int(np.sum(valid_mask))
            total_pixels = int(np.sum(rotated_mask))
            out_of_bounds_pixels += (total_pixels - pixels_on_board)

        # calculating elements for the objective function

        # pixels out of the bounds of our given paper
        out_of_bounds_pixels = out_of_bounds_pixels

        # pixels where there is more than one fragment
        overlap_pixels = int(np.sum(board[board > 1] - 1))

        # filled area in the fragments' bounding box - counts the gaps between fragments
        active_pixels = np.where(board > 0)
        if len(active_pixels[0]) > 0:
            min_y, max_y = np.min(active_pixels[0]), np.max(active_pixels[0])
            min_x, max_x = np.min(active_pixels[1]), np.max(active_pixels[1])
            bbox_area = (max_x - min_x) * (max_y - min_y)
            filled_area = int(np.sum(board > 0))
            empty_gaps = max(0, bbox_area - filled_area)
        else:
            empty_gaps = self.width * self.height

        # contact length of two fragments (pixels where two borders meet)
        seam_mask = (seam_count >= 2) & (board == 0)
        contact_length = int(np.sum(seam_mask))
        
        touching_pairs = set()
        ink_seam_pixels = 0

        if contact_length > 0:
            n = seam_count[seam_mask].astype(np.float32)
            mean_val = seam_color_sum[seam_mask] / n
            mean_sq_val = seam_color_sq_sum[seam_mask] / n
            squared_diff = np.maximum(0.0, mean_sq_val - (mean_val ** 2))

            # color mismatch on the conection points for two fragments
            total_color_mismatch = float(np.sum(squared_diff))

            # Reward seam pixels where dark ink/lines (mean_val < 205) match across both fragments (squared_diff < 900)
            # text continuity
            matching_ink_mask = (mean_val < 205.0) & (squared_diff < 900.0)
            ink_seam_pixels = int(np.sum(matching_ink_mask))

            unique_masks, counts = np.unique(border_id_board[seam_mask], return_counts=True)
            for bmask, px_cnt in zip(unique_masks, counts):
                if px_cnt < 6:
                    continue
                active_ids = [idx for idx in range(min(num_frags, 63)) if (int(bmask) & (1 << idx))]
                for a_i in range(len(active_ids)):
                    for b_i in range(a_i + 1, len(active_ids)):
                        touching_pairs.add((active_ids[a_i], active_ids[b_i]))
        else:
            total_color_mismatch = 1e6

        # closed cycles in the graph
        closed_cycles = max(0, len(touching_pairs) - (num_frags - 1))

        score = (self.w_overlap * overlap_pixels) + \
                (self.w_out * out_of_bounds_pixels) + \
                (self.w_compact * empty_gaps) - \
                (self.w_edge_len * contact_length) + \
                (self.w_color_diff * total_color_mismatch) - \
                (self.w_cycle * closed_cycles) - \
                (self.w_ink_match * ink_seam_pixels)
                
        return float(score), frozenset(touching_pairs)

    def evaluate(self, chromosome) -> float:
        score, _ = self.evaluate_with_graph(chromosome)
        return score

def jaccard_similarity(pairs_a: frozenset, pairs_b: frozenset) -> float:
    """
    Calculating the jaccard similarity - measure of similarity between sets calculated as
    the ratio of the intersection to the sum of those sets.
    """
    if not pairs_a and not pairs_b:
        return 1.0
    union_len = len(pairs_a | pairs_b)
    if union_len == 0:
        return 0.0
    return len(pairs_a & pairs_b) / union_len


def jaccard_tournament_selection(population, scores, pair_sets, pop_size, k=3, max_jaccard=0.85):
    """
    Elitist tournament selection with Jaccard diversity filtering (Sizikova & Funkhouser, Sec. 4.2).
    Prevents the population from collapsing into identical clones.
    """
    sorted_indices = np.argsort(scores)
    
    # Always preserve the single best individual (elitism)
    best_idx = sorted_indices[0]
    new_population = [copy.deepcopy(population[best_idx])]
    new_scores = [scores[best_idx]]
    accepted_pair_sets = [pair_sets[best_idx]]
    
    total_pool_size = len(population)
    attempts = 0
    max_attempts = pop_size * 10

    # tournament selection
    while len(new_population) < pop_size and attempts < max_attempts:
        attempts += 1
        participants_idx = np.random.choice(total_pool_size, size=min(k, total_pool_size), replace=False)
        winner_idx = participants_idx[np.argmin(scores[participants_idx])]
        cand_pairs = pair_sets[winner_idx]
        
        # Reject candidate if it is too similar (J > 0.85) to an already selected individual
        # to avoid filling the population with identical clones
        is_duplicate = any(
            jaccard_similarity(cand_pairs, existing_pairs) > max_jaccard
            for existing_pairs in accepted_pair_sets
        )
        if is_duplicate:
            continue
            
        new_population.append(copy.deepcopy(population[winner_idx]))
        new_scores.append(scores[winner_idx])
        accepted_pair_sets.append(cand_pairs)
        
    # Fill any remaining slots if diversity filter was too strict
    if len(new_population) < pop_size:
        for idx in sorted_indices:
            if len(new_population) >= pop_size:
                break
            new_population.append(copy.deepcopy(population[idx]))
            new_scores.append(scores[idx])
            accepted_pair_sets.append(pair_sets[idx])
            
    return new_population, np.array(new_scores), accepted_pair_sets

def _transform_point(pt, orig_w, orig_h, angle_deg):
    """
    Calculates the new (x, y) coordinates of a local point within a fragment
    after the fragment is rotated with an expanded bounding box.
    """
    center_x, center_y = orig_w // 2, orig_h // 2
    M = cv2.getRotationMatrix2D((center_x, center_y), angle_deg, 1.0)
    
    cos_val = np.abs(M[0, 0])
    sin_val = np.abs(M[0, 1])
    new_w = int((orig_h * sin_val) + (orig_w * cos_val))
    new_h = int((orig_h * cos_val) + (orig_w * sin_val))
    
    M[0, 2] += (new_w / 2.0) - center_x
    M[1, 2] += (new_h / 2.0) - center_y
    
    px, py = pt
    rot_x = M[0, 0] * px + M[0, 1] * py + M[0, 2]
    rot_y = M[1, 0] * px + M[1, 1] * py + M[1, 2]
    
    return (rot_x, rot_y), new_w, new_h

def decode_path_to_layout(chromosome, fragments, contour_anchors, board_width, board_height):
    """
    Converts a path-based chromosome into global [x, y, rot] coordinates for each fragment.
    Automatically centers the assembled cluster onto the target board.
    
    Returns:
        list[list[float]]: A list ordered by fragment index (0 to N-1), where each element
                           is [top_left_x, top_left_y, rotation_degrees].
    """
    num_fragments = len(fragments)
    layout = [None] * num_fragments
    
    # Placing the root anchor fragment at the origin (0, 0) initially
    root_gene = chromosome[0]
    root_idx = root_gene['frag_idx']
    root_rot = root_gene['base_rot']
    
    root_h, root_w = fragments[root_idx].data.shape[:2]
    _, root_new_w, root_new_h = _transform_point((0, 0), root_w, root_h, root_rot)
    
    layout[root_idx] = [0.0, 0.0, root_rot]
    
    # Track bounding box of the entire assembled structure
    min_x, min_y = 0.0, 0.0
    max_x, max_y = float(root_new_w), float(root_new_h)
    
    # Sequentially attach each piece to the previous piece in the path
    for step in range(1, len(chromosome)):
        curr_gene = chromosome[step]
        prev_gene = chromosome[curr_gene['parent_step']]
        
        prev_idx = prev_gene['frag_idx']
        curr_idx = curr_gene['frag_idx']
        
        prev_x, prev_y, prev_rot = layout[prev_idx]
        prev_h, prev_w = fragments[prev_idx].data.shape[:2]
        curr_h, curr_w = fragments[curr_idx].data.shape[:2]
        
        # Fallback if a fragment has no contour anchors
        if not contour_anchors[prev_idx] or not contour_anchors[curr_idx]:
            layout[curr_idx] = [prev_x + 10.0, prev_y + 10.0, 0.0]
            continue

        p_idx = curr_gene['parent_anchor_idx'] % len(contour_anchors[prev_idx])
        c_idx = curr_gene['child_anchor_idx'] % len(contour_anchors[curr_idx])
        p_anchor = contour_anchors[prev_idx][p_idx]
        c_anchor = contour_anchors[curr_idx][c_idx]
        
        # Global tangent angle of parent anchor in screen space:
        parent_global_tangent = (p_anchor['angle'] - prev_rot) % 360.0
        
        # Two mating edges must run in opposite directions (180 degrees apart)
        target_child_global_tangent = (parent_global_tangent + 180.0 + curr_gene['angle_offset']) % 360.0
        curr_rot = (c_anchor['angle'] - target_child_global_tangent) % 360.0
        
        # Find global position of the parent's anchor point
        (p_rot_x, p_rot_y), _, _ = _transform_point(p_anchor['pt'], prev_w, prev_h, prev_rot)
        parent_global_pt_x = prev_x + p_rot_x
        parent_global_pt_y = prev_y + p_rot_y
        
        # Find local rotated position of the child's anchor point
        (c_rot_x, c_rot_y), curr_new_w, curr_new_h = _transform_point(c_anchor['pt'], curr_w, curr_h, curr_rot)

        # Align child's anchor point onto parent's anchor point + continuous slide along the seam
        slide = curr_gene.get('slide_offset', 0.0)
        tangent_rad = math.radians(parent_global_tangent)
        slide_dx = slide * math.cos(tangent_rad)
        slide_dy = slide * math.sin(tangent_rad)

        curr_x = parent_global_pt_x + slide_dx - c_rot_x
        curr_y = parent_global_pt_y + slide_dy - c_rot_y    
        
        layout[curr_idx] = [curr_x, curr_y, curr_rot]
        
        # Update global bounding box
        min_x = min(min_x, curr_x)
        min_y = min(min_y, curr_y)
        max_x = max(max_x, curr_x + curr_new_w)
        max_y = max(max_y, curr_y + curr_new_h)

    # Center the assembled cluster onto the target board so it doesn't drift off-screen
    cluster_center_x = (min_x + max_x) / 2.0
    cluster_center_y = (min_y + max_y) / 2.0
    
    board_center_x = board_width / 2.0
    board_center_y = board_height / 2.0
    
    shift_x = board_center_x - cluster_center_x
    shift_y = board_center_y - cluster_center_y
    
    for i in range(num_fragments):
        layout[i][0] += shift_x
        layout[i][1] += shift_y
        
    return layout

def mutate_path(chromosome, contour_anchors, progress):
    """
    Mutates a tree-based chromosome by altering fragment order, tree parent links,
    or fine-tuning anchor points using text-aligned compatibility.
    """
    mutated = copy.deepcopy(chromosome)
    num_genes = len(mutated)
    # simulated annealing
    temp = max(0.05, 1.0 - progress)
    
    # Structural Mutation: swap two fragments in the order
    if random.random() < 0.4 * temp:
        idx1, idx2 = random.sample(range(num_genes), 2)
        
        mutated[idx1]['frag_idx'], mutated[idx2]['frag_idx'] = (
            mutated[idx2]['frag_idx'], 
            mutated[idx1]['frag_idx']
        )

        # If root (idx 0) changed, update its upright base_rot
        if idx1 == 0 or idx2 == 0:
            root_frag = mutated[0]['frag_idx']
            root_text = contour_anchors[root_frag][0]['text_angle'] if contour_anchors[root_frag] else None
            mutated[0]['base_rot'] = root_text if root_text is not None else 0.0
        
        # Repair any invalid parent_step links and re-match anchors for affected nodes
        for idx in range(1, num_genes):
            p_step = mutated[idx].get('parent_step', idx - 1)
            # Enforce parent_step < idx so parent is always decoded before child
            if p_step >= idx or p_step < 0:
                p_step = random.randint(0, idx - 1)
                mutated[idx]['parent_step'] = p_step

            if idx in {idx1, idx2} or p_step in {idx1, idx2}:
                prev_frag = mutated[p_step]['frag_idx']
                curr_frag = mutated[idx]['frag_idx']
                
                num_p = len(contour_anchors[prev_frag])
                p_anc_idx = random.randint(0, max(0, num_p - 1))
                mutated[idx]['parent_anchor_idx'] = p_anc_idx
                
                if num_p > 0 and contour_anchors[curr_frag]:
                    mutated[idx]['child_anchor_idx'] = pick_compatible_child_anchor(
                        contour_anchors[prev_frag][p_anc_idx],
                        contour_anchors[curr_frag],
                        p_frag=prev_frag,
                        p_idx=p_anc_idx,
                        c_frag=curr_frag
                    )
                else:
                    mutated[idx]['child_anchor_idx'] = 0

    # Local Connection Mutation: adjust tree attachment, anchor points, and angle offsets
    num_local_mutations = random.randint(1, max(1, num_genes // 4))
    target_indices = random.sample(range(num_genes), num_local_mutations)
    
    for idx in target_indices:
        if idx == 0:
            # Keep root aligned with text (allow 180-deg flip or tiny tilt)
            if random.random() < 0.2 * temp:
                # Rotate everything by 180-deg
                mutated[0]['base_rot'] = (mutated[0]['base_rot'] + 180.0) % 360.0
            else:
                # Rotate everything by a small degree
                mutated[0]['base_rot'] = (mutated[0]['base_rot'] + random.uniform(-5.0 * temp, 5.0 * temp)) % 360.0
        else:
            # Occasionally re-attach this fragment to a different parent fragment in the tree
            if random.random() < 0.45 * temp:
                mutated[idx]['parent_step'] = random.randint(0, idx - 1)

            p_step = mutated[idx]['parent_step']
            prev_frag = mutated[p_step]['frag_idx']
            curr_frag = mutated[idx]['frag_idx']
            
            num_p_anchors = len(contour_anchors[prev_frag])
            num_c_anchors = len(contour_anchors[curr_frag])
            
            if num_p_anchors > 0:
                if random.random() < 0.25 * temp:
                    # Big jump to a different edge on parent -> pick compatible child anchor
                    p_anc_idx = random.randint(0, num_p_anchors - 1)
                    mutated[idx]['parent_anchor_idx'] = p_anc_idx
                    if num_c_anchors > 0:
                        mutated[idx]['child_anchor_idx'] = pick_compatible_child_anchor(
                            contour_anchors[prev_frag][p_anc_idx],
                            contour_anchors[curr_frag],
                            p_frag=prev_frag,
                            p_idx=p_anc_idx,
                            c_frag=curr_frag
                        )
                else:
                    step_shift = random.choice([-1, 0, 1])
                    new_p_idx = (mutated[idx]['parent_anchor_idx'] + step_shift) % num_p_anchors
                    mutated[idx]['parent_anchor_idx'] = new_p_idx

                    if num_c_anchors > 0:
                        mutated[idx]['child_anchor_idx'] = pick_compatible_child_anchor(
                            contour_anchors[prev_frag][new_p_idx],
                            contour_anchors[curr_frag],
                            p_frag=prev_frag,
                            p_idx=new_p_idx,
                            c_frag=curr_frag
                        )

            # Fine-tune continuous slide along the seam (closes 1..15 px steps & diagonal gaps)
            cur_slide = mutated[idx].get('slide_offset', 0.0)
            cur_slide += random.gauss(0, 4.0 * temp + 1.0)
            mutated[idx]['slide_offset'] = max(-14.0, min(14.0, cur_slide))

            mutated[idx]['angle_offset'] += random.uniform(-1.0 * temp, 1.0 * temp)
            mutated[idx]['angle_offset'] = max(-2.5, min(2.5, mutated[idx]['angle_offset']))

    return mutated

def crossover_path(parent1, parent2, contour_anchors):
    """
    Subtree-preserving crossover (inspired by cluster recombination in Sizikova & Funkhouser):
    Extracts an intact connected sub-tree (cluster) from parent1 with all its internal anchor
    connections preserved, and fills the remaining fragments using parent2's structure.
    """
    def _extract_subtree_indices(chrom, root_step):
        selected = {root_step}
        added = True
        while added:
            added = False
            for s in range(root_step + 1, len(chrom)):
                if s not in selected and chrom[s].get('parent_step', -1) in selected:
                    selected.add(s)
                    added = True
        return sorted(selected)

    def _build_child(p1, p2):
        size = len(p1)
        # Pick a non-trivial subtree root from p1 (not index 0 so we don't copy the whole tree)
        sub_root = random.randint(1, max(1, size - 1))
        subtree_steps = _extract_subtree_indices(p1, sub_root)

        # Fallback to a 2-node pair if subtree is too large (> 75% of all fragments)
        if len(subtree_steps) > max(2, int(size * 0.75)):
            subtree_steps = [sub_root]

        subtree_frags = {p1[s]['frag_idx'] for s in subtree_steps}

        # Remaining fragments taken in the order they appear in p2
        p2_remaining = [g for g in p2 if g['frag_idx'] not in subtree_frags]

        child = []
        old_step_to_new_step = {}
        frag_to_new_step = {}

        # Place p2_remaining fragments first (preserving their relative tree links where possible)
        for p2_gene in p2_remaining:
            new_step = len(child)
            frag_id = p2_gene['frag_idx']
            frag_to_new_step[frag_id] = new_step

            if new_step == 0:
                root_text = contour_anchors[frag_id][0]['text_angle'] if contour_anchors[frag_id] else None
                base_rot = p2_gene.get('base_rot', root_text if root_text is not None else 0.0)
                child.append({
                    'frag_idx': frag_id,
                    'base_rot': base_rot
                })
            else:
                # Check if original parent fragment from p2 is already placed earlier in child
                orig_p_step = p2_gene.get('parent_step', -1)
                orig_p_frag = p2[orig_p_step]['frag_idx'] if 0 <= orig_p_step < size else -1

                if orig_p_frag in frag_to_new_step and frag_to_new_step[orig_p_frag] < new_step:
                    # Preserve exact parent & anchors from p2!
                    child.append({
                        'frag_idx': frag_id,
                        'parent_step': frag_to_new_step[orig_p_frag],
                        'parent_anchor_idx': p2_gene.get('parent_anchor_idx', 0),
                        'child_anchor_idx': p2_gene.get('child_anchor_idx', 0),
                        'angle_offset': p2_gene.get('angle_offset', 0.0)
                    })
                else:
                    # Attach to a valid earlier fragment using compatible anchors
                    p_step = random.randint(0, new_step - 1)
                    prev_frag_id = child[p_step]['frag_idx']
                    num_p = len(contour_anchors[prev_frag_id])
                    p_anc = random.randint(0, max(0, num_p - 1))
                    c_anc = (
                        pick_compatible_child_anchor(
                            contour_anchors[prev_frag_id][p_anc], 
                            contour_anchors[frag_id],
                            p_frag=prev_frag_id,
                            p_idx=p_anc,
                            c_frag=frag_id
                            )
                        if num_p > 0 and contour_anchors[frag_id] else 0
                    )
                    child.append({
                        'frag_idx': frag_id,
                        'parent_step': p_step,
                        'parent_anchor_idx': p_anc,
                        'child_anchor_idx': c_anc,
                        'angle_offset': random.uniform(-2.0, 2.0)
                    })

        # Attach the intact subtree cluster from p1 onto the already placed fragments
        for idx_in_sub, orig_step in enumerate(subtree_steps):
            new_step = len(child)
            old_step_to_new_step[orig_step] = new_step
            src_gene = p1[orig_step]
            frag_id = src_gene['frag_idx']

            if idx_in_sub == 0:
                # Root of the transplanted subtree attaches to the main body via compatible anchors
                p_step = random.randint(0, new_step - 1)
                prev_frag_id = child[p_step]['frag_idx']
                num_p = len(contour_anchors[prev_frag_id])
                p_anc = random.randint(0, max(0, num_p - 1))
                c_anc = (
                    pick_compatible_child_anchor(
                        contour_anchors[prev_frag_id][p_anc], 
                        contour_anchors[frag_id],
                        p_frag=prev_frag_id,
                        p_idx=p_anc,
                        c_frag=frag_id
                        )
                    if num_p > 0 and contour_anchors[frag_id] else 0
                )
                child.append({
                    'frag_idx': frag_id,
                    'parent_step': p_step,
                    'parent_anchor_idx': p_anc,
                    'child_anchor_idx': c_anc,
                    'angle_offset': src_gene.get('angle_offset', 0.0)
                })
            else:
                # Internal nodes of the subtree keep their EXACT parent_step and anchors!
                mapped_parent = old_step_to_new_step[src_gene['parent_step']]
                child.append({
                    'frag_idx': frag_id,
                    'parent_step': mapped_parent,
                    'parent_anchor_idx': src_gene['parent_anchor_idx'],
                    'child_anchor_idx': src_gene['child_anchor_idx'],
                    'angle_offset': src_gene['angle_offset']
                })

        return child

    return _build_child(parent1, parent2), _build_child(parent2, parent1)

def estimate_fragment_text_angle(frag_data: np.ndarray):
    """
    Estimates the upright text line angle in [0, 360) degrees without aspect-ratio bias.
    Uses square crops so tall/narrow strips do not falsely favor 90-degree vertical alignment.
    """
    alpha = frag_data[:, :, 3]
    gray = cv2.cvtColor(frag_data[:, :, :3], cv2.COLOR_BGR2GRAY)
    mask = alpha > 127

    # Adaptive ink threshold relative to local paper brightness
    paper_val = float(np.percentile(gray[mask], 75)) if np.any(mask) else 220.0
    ink = ((gray < (paper_val - 35.0)) & mask).astype(np.uint8)
    if np.sum(ink) < 120:
        return None

    # Extract dense square patches of ink so width == height (eliminates strip aspect-ratio bias)
    ys, xs = np.where(ink > 0)
    y1, y2 = int(np.min(ys)), int(np.max(ys)) + 1
    x1, x2 = int(np.min(xs)), int(np.max(xs)) + 1
    cropped = ink[y1:y2, x1:x2]

    patch_size = 140
    patches = []
    ch, cw = cropped.shape
    step = patch_size // 2
    for py in range(0, max(1, ch - patch_size // 2), step):
        for px in range(0, max(1, cw - patch_size // 2), step):
            sub = cropped[py : py + patch_size, px : px + patch_size]
            if np.sum(sub) > 60:
                padded = np.zeros((patch_size, patch_size), dtype=np.uint8)
                padded[:sub.shape[0], :sub.shape[1]] = sub
                patches.append(padded)

    if not patches:
        side = max(ch, cw)
        padded = np.zeros((side, side), dtype=np.uint8)
        padded[:ch, :cw] = cropped
        if side > 220:
            padded = cv2.resize(padded, (220, 220), interpolation=cv2.INTER_NEAREST)
        patches = [padded]

    # Limit to at most 8 richest patches for speed
    patches.sort(key=lambda p: int(np.sum(p)), reverse=True)
    patches = patches[:8]

    best_angle = 0.0
    best_score = -1.0

    for angle in np.arange(-90.0, 90.0, 2.0):
        total_score = 0.0
        for p in patches:
            ph, pw = p.shape
            M = cv2.getRotationMatrix2D((pw // 2, ph // 2), angle, 1.0)
            rot = cv2.warpAffine(p, M, (pw, ph), flags=cv2.INTER_NEAREST)
            row_sums = np.sum(rot, axis=1, dtype=np.float32)
            # Normalize by active rows to measure sharpness of line-to-gap transitions
            total_score += float(np.var(row_sums))
        if total_score > best_score:
            best_score = total_score
            best_angle = float(angle)

    for angle in np.arange(best_angle - 2.0, best_angle + 2.1, 0.25):
        total_score = 0.0
        for p in patches:
            ph, pw = p.shape
            M = cv2.getRotationMatrix2D((pw // 2, ph // 2), angle, 1.0)
            rot = cv2.warpAffine(p, M, (pw, ph), flags=cv2.INTER_NEAREST)
            row_sums = np.sum(rot, axis=1, dtype=np.float32)
            total_score += float(np.var(row_sums))
        if total_score > best_score:
            best_score = total_score
            best_angle = float(angle)

    # Resolve 180-degree flip via ascender asymmetry on the primary patch
    p0 = patches[0]
    ph, pw = p0.shape
    M_up = cv2.getRotationMatrix2D((pw // 2, ph // 2), best_angle, 1.0)
    rot_up = cv2.warpAffine(p0, M_up, (pw, ph), flags=cv2.INTER_NEAREST)
    row_profile = np.sum(rot_up, axis=1, dtype=np.float32)

    diffs = np.diff(row_profile)
    top_heavy = float(np.sum(np.maximum(0.0, diffs) ** 2))
    bottom_heavy = float(np.sum(np.maximum(0.0, -diffs) ** 2))

    if bottom_heavy > top_heavy * 1.12:
        best_angle = (best_angle + 180.0) % 360.0

    return best_angle % 360.0


def extract_contour_anchors(fragments, ocr_known=None, step_px: int = 16, min_edge_len: float = 50.0):
    """
    Extracts anchor points along straight edges, storing a 1D intensity & ink profile
    around each anchor so matching compares actual text lines and paper shading across seams.
    """
    all_fragments_anchors = []

    for idx, frag in enumerate(fragments):
        alpha = frag.data[:, :, 3]
        gray = cv2.cvtColor(frag.data[:, :, :3], cv2.COLOR_BGR2GRAY).astype(np.float32)
        gray_smooth = cv2.GaussianBlur(gray, (3, 3), 0)
        h, w = gray.shape

        binary_mask = (alpha > 127).astype(np.uint8)
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

        if not contours:
            all_fragments_anchors.append([])
            continue

        if ocr_known is not None and ocr_known[idx]:
            text_angle = 0.0
        else:
            text_angle = estimate_fragment_text_angle(frag.data)

        main_contour = max(contours, key=cv2.contourArea)

        epsilon = 0.012 * cv2.arcLength(main_contour, True)
        poly = cv2.approxPolyDP(main_contour, epsilon, True).reshape(-1, 2)
        num_vertices = len(poly)

        anchors = []
        # Half-window in pixels sampled along the edge around each anchor (total patch = 64 px)
        half_win = 32
        win_offsets = np.linspace(-half_win, half_win, 33, dtype=np.float32)

        for i in range(num_vertices):
            p1 = poly[i].astype(float)
            p2 = poly[(i + 1) % num_vertices].astype(float)

            edge_vec = p2 - p1
            edge_len = float(np.linalg.norm(edge_vec))

            if edge_len < min_edge_len:
                continue

            unit_tangent = edge_vec / edge_len
            tangent_angle = math.degrees(math.atan2(edge_vec[1], edge_vec[0]))

            perp_left = np.array([-unit_tangent[1], unit_tangent[0]])
            perp_right = -perp_left
            mid = (p1 + p2) * 0.5
            test_pt = np.clip(np.round(mid + perp_left * 5.0).astype(int), [0, 0], [w - 1, h - 1])
            inward_normal = perp_left if binary_mask[test_pt[1], test_pt[0]] > 0 else perp_right

            num_samples = max(1, int((edge_len * 0.8) // step_px))
            for s in range(num_samples):
                t = 0.1 + 0.8 * ((s + 0.5) / num_samples)
                pt = p1 + t * edge_vec

                # Sample a 1D strip along the edge (averaged 2..5 px inward) to capture text rows & shading
                strip_samples = []
                for d in (2.0, 3.5, 5.0):
                    pts = pt[None, :] + win_offsets[:, None] * unit_tangent[None, :] + inward_normal[None, :] * d
                    xs = np.clip(np.round(pts[:, 0]).astype(int), 0, w - 1)
                    ys = np.clip(np.round(pts[:, 1]).astype(int), 0, h - 1)
                    strip_samples.append(gray_smooth[ys, xs])

                strip_profile = np.mean(strip_samples, axis=0)
                grad_profile = np.diff(strip_profile)
                profile_std = float(np.std(strip_profile))

                anchors.append({
                    'pt': (float(pt[0]), float(pt[1])),
                    'angle': tangent_angle,
                    'edge_len': edge_len,
                    'text_angle': text_angle,
                    'strip_profile': strip_profile,
                    'grad_profile': grad_profile,
                    'profile_std': profile_std,
                    't_pos': float(t)
                })

        all_fragments_anchors.append(anchors)

    return all_fragments_anchors

PAIRWISE_MATCH_CACHE = {}


def precompute_pairwise_matches(contour_anchors, top_k: int = 5):
    """
    Stage 1 (Funkhouser et al. pairwise matching):
    Precomputes and prunes the top-K best anchor matches between every ordered pair
    of fragments using 1D color profiles, 1D gradient (stroke) profiles, edge lengths,
    and text line orientation.
    """
    global PAIRWISE_MATCH_CACHE
    PAIRWISE_MATCH_CACHE = {}
    num_frags = len(contour_anchors)

    for p_frag in range(num_frags):
        p_list = contour_anchors[p_frag]
        if not p_list:
            continue

        for p_idx, p_anc in enumerate(p_list):
            p_text = p_anc['text_angle']
            p_edge_angle = p_anc['angle']
            p_len = p_anc['edge_len']
            p_prof = p_anc['strip_profile']
            p_grad = p_anc['grad_profile']
            p_std = p_anc['profile_std']

            for c_frag in range(num_frags):
                if p_frag == c_frag:
                    continue
                c_list = contour_anchors[c_frag]
                if not c_list:
                    continue

                candidates = []
                for c_idx, c_anc in enumerate(c_list):
                    c_text = c_anc['text_angle']
                    c_edge_angle = c_anc['angle']

                    # 1. Text orientation filter (rejects 90/270-deg turns)
                    if p_text is not None and c_text is not None:
                        rel_rot = (c_edge_angle - p_edge_angle - 180.0) % 360.0
                        aligned_c_text = (c_text - rel_rot) % 360.0
                        diff = abs(aligned_c_text - (p_text % 360.0))
                        diff = min(diff, 360.0 - diff)

                        if diff <= 10.0:
                            angle_score = 1.0 / (1.0 + diff)
                        elif abs(diff - 180.0) <= 10.0:
                            angle_score = 0.25 / (1.0 + abs(diff - 180.0))
                        else:
                            continue
                    else:
                        angle_score = 0.4

                    # 2. 1D intensity similarity (reversed along mating edge)
                    c_prof_rev = c_anc['strip_profile'][::-1]
                    color_mse = float(np.mean((p_prof - c_prof_rev) ** 2))
                    color_score = 1.0 / (1.0 + (color_mse / 140.0))

                    # 3. 1D gradient similarity (matches text line boundaries across illumination shifts)
                    # Reversing edge direction negates the derivative sign
                    c_grad_rev = -c_anc['grad_profile'][::-1]
                    grad_mse = float(np.mean((p_grad - c_grad_rev) ** 2))
                    grad_score = 1.0 / (1.0 + (grad_mse / 60.0))

                    # 4. Content richness bonus (prefers edges with actual text/lines over blank margins)
                    shared_texture = min(p_std, c_anc['profile_std'])
                    texture_bonus = 1.0 + min(5.0, shared_texture / 8.0)

                    # 5. Edge length similarity
                    len_ratio = min(p_len, c_anc['edge_len']) / max(p_len, c_anc['edge_len'])
                    len_score = 0.4 + 0.6 * (len_ratio ** 2)

                    weight = angle_score * color_score * grad_score * texture_bonus * len_score + 1e-6
                    candidates.append((c_idx, weight))

                if candidates:
                    # Prune to top-K strongest matches for this (p_frag, p_idx, c_frag) triple
                    candidates.sort(key=lambda x: x[1], reverse=True)
                    top_candidates = candidates[:top_k]
                    c_indices = [item[0] for item in top_candidates]
                    c_weights = [item[1] for item in top_candidates]
                    PAIRWISE_MATCH_CACHE[(p_frag, p_idx, c_frag)] = (c_indices, c_weights)

def pick_compatible_child_anchor(parent_anchor: dict, child_anchors: list,
                                 p_frag: int = None, p_idx: int = None, c_frag: int = None) -> int:
    """
    Uses precomputed Funkhouser pairwise matches when available (PAIRWISE_MATCH_CACHE),
    otherwise evaluates all compatible child anchors dynamically.
    """
    if not child_anchors:
        return 0

    # With the Funkhouser's algorithm (as it's used in the article) for the initial edge matching
    if PAIRWISE_MATCH_CACHE and p_frag is not None and p_idx is not None and c_frag is not None:
        cached = PAIRWISE_MATCH_CACHE.get((p_frag, p_idx, c_frag))
        if cached is not None:
            c_indices, c_weights = cached
            return random.choices(c_indices, weights=c_weights, k=1)[0]

    p_text = parent_anchor['text_angle']
    p_edge_angle = parent_anchor['angle']
    p_len = parent_anchor['edge_len']
    p_prof = parent_anchor['strip_profile']
    p_std = parent_anchor['profile_std']

    valid_indices = []
    weights = []

    for idx, c_anc in enumerate(child_anchors):
        c_text = c_anc['text_angle']
        c_edge_angle = c_anc['angle']

        if p_text is not None and c_text is not None:
            rel_rot = (c_edge_angle - p_edge_angle - 180.0) % 360.0
            aligned_c_text = (c_text - rel_rot) % 360.0
            diff = abs(aligned_c_text - (p_text % 360.0))
            diff = min(diff, 360.0 - diff)

            if diff <= 10.0:
                angle_score = 1.0 / (1.0 + diff)
            elif abs(diff - 180.0) <= 10.0:
                angle_score = 0.25 / (1.0 + abs(diff - 180.0))
            else:
                continue
        else:
            angle_score = 0.4

        c_prof_rev = c_anc['strip_profile'][::-1]
        mse = float(np.mean((p_prof - c_prof_rev) ** 2))
        profile_score = 1.0 / (1.0 + (mse / 150.0))

        shared_texture = min(p_std, c_anc['profile_std'])
        texture_bonus = 1.0 + min(4.0, shared_texture / 10.0)

        len_ratio = min(p_len, c_anc['edge_len']) / max(p_len, c_anc['edge_len'])
        len_score = 0.5 + 0.5 * len_ratio

        valid_indices.append(idx)
        weights.append(angle_score * profile_score * texture_bonus * len_score + 1e-6)

    if not valid_indices:
        return random.randint(0, len(child_anchors) - 1)

    return random.choices(valid_indices, weights=weights, k=1)[0]

class EvolutionaryAlgorithm:
    def __init__(self, objective_func, mutation_op, crossover_op, selection_op, 
                 fragments, contour_anchors, pop_size=100, crossover_prob=0.8, mutation_prob=0.25):
        self.objective_func = objective_func
        self.mutation_op = mutation_op
        self.crossover_op = crossover_op
        self.selection_op = selection_op

        self.fragments = fragments
        self.contour_anchors = contour_anchors
        self.pop_size = pop_size
        self.num_fragments = len(fragments)

        self.crossover_prob = crossover_prob
        self.mutation_prob = mutation_prob

        # Initialization
        self.population = self._initialize_population()

    def _initialize_population(self):
        """
        Generates an initial population of 2D fragment trees with text-aligned anchors.
        """
        population = []
        
        for _ in range(self.pop_size):
            order = list(range(self.num_fragments))
            random.shuffle(order)
            
            chromosome = []
            
            # STEP 0: Root anchor fragment (orient upright using detected text angle)
            first_frag = order[0]
            root_text_angle = (
                self.contour_anchors[first_frag][0]['text_angle']
                if self.contour_anchors[first_frag] else None
            )
            base_rot = root_text_angle if root_text_angle is not None else 0.0

            chromosome.append({
                'frag_idx': first_frag,
                'base_rot': base_rot
            })
            
            # STEPS 1 .. N-1: Attach each piece to ANY earlier piece (0 .. step - 1)
            for step in range(1, self.num_fragments):
                parent_step = random.randint(0, step - 1)
                prev_frag = order[parent_step]
                curr_frag = order[step]
                
                num_prev_anchors = len(self.contour_anchors[prev_frag])
                parent_anchor = random.randint(0, max(0, num_prev_anchors - 1))
                
                if num_prev_anchors > 0 and self.contour_anchors[curr_frag]:
                    p_anc = self.contour_anchors[prev_frag][parent_anchor]
                    child_anchor = pick_compatible_child_anchor(
                        p_anc, 
                        self.contour_anchors[curr_frag],
                        p_frag=prev_frag,
                        p_idx=parent_anchor,
                        c_frag=curr_frag
                        )
                else:
                    child_anchor = 0
                
                chromosome.append({
                    'frag_idx': curr_frag,
                    'parent_step': parent_step,
                    'parent_anchor_idx': parent_anchor,
                    'child_anchor_idx': child_anchor,
                    'angle_offset': random.uniform(-3.0, 3.0)
                })
                
            population.append(chromosome)
            
        return population
        
    def train(self, generations=1000):
        # Initial evaluation
        eval_results = [self.objective_func(ind) for ind in tqdm(self.population, desc="Initialization")]
        scores = np.array([r[0] for r in eval_results])
        pair_sets = [r[1] for r in eval_results]

        history_best = []
        history_all = []

        pbar = tqdm(range(generations), desc="Evolution")
        for gen in pbar:
            progress = gen / generations
            children = []

            # CROSSOVER
            indices = np.arange(self.pop_size)
            np.random.shuffle(indices)

            for i in range(0, self.pop_size - 1, 2):
                parent1 = self.population[indices[i]]
                parent2 = self.population[indices[i+1]]
                
                if np.random.rand() < self.crossover_prob:
                    child1, child2 = self.crossover_op(parent1, parent2, self.contour_anchors)
                else:
                    child1, child2 = copy.deepcopy(parent1), copy.deepcopy(parent2)
                    
                children.extend([child1, child2])

            # MUTATION
            mutated_children = []
            for child in children:
                if np.random.rand() < self.mutation_prob:
                    mutated_children.append(self.mutation_op(child, self.contour_anchors, progress))
                else:
                    mutated_children.append(child)

            # EVALUATION
            child_results = [self.objective_func(c) for c in mutated_children]
            children_scores = np.array([r[0] for r in child_results])
            children_pairs = [r[1] for r in child_results]

            # SELECTION WITH JACCARD FILTER
            combined_population = self.population + mutated_children
            combined_scores = np.concatenate((scores, children_scores))
            combined_pairs = pair_sets + children_pairs

            self.population, scores, pair_sets = self.selection_op(
                combined_population,
                combined_scores,
                combined_pairs,
                self.pop_size
            )

            best_current_score = np.min(scores)
            pbar.set_postfix({"best_score": round(best_current_score, 2)})
            
            history_best.append(best_current_score)
            history_all.append(scores.copy())
        
        best_idx = np.argmin(scores)
        best_individual = self.population[best_idx]
        best_score = scores[best_idx]
        
        return best_individual, best_score, history_best, history_all

def render_reconstruction(best_chromosome, fragments, board_width, board_height):
    # Finding global bounding box
    min_x, min_y = 0, 0 
    max_x, max_y = board_width, board_height 
    
    placed_pieces = []
    
    for i, gene in enumerate(best_chromosome):
        x, y, rot = gene
        fragment = fragments[i]
        
        h, w = fragment.data.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, rot, 1.0)
        
        cos_val = np.abs(M[0, 0])
        sin_val = np.abs(M[0, 1])
        new_w = int((h * sin_val) + (w * cos_val))
        new_h = int((h * cos_val) + (w * sin_val))
        
        start_x = int(x)
        start_y = int(y)
        
        min_x = min(min_x, start_x)
        min_y = min(min_y, start_y)
        max_x = max(max_x, start_x + new_w)
        max_y = max(max_y, start_y + new_h)
        
        placed_pieces.append({
            'fragment': fragment, 'x': start_x, 'y': start_y, 'rot': rot,
            'new_w': new_w, 'new_h': new_h, 'center': center
        })
        
    # Bigger dynamic canvas
    canvas_width = max_x - min_x
    canvas_height = max_y - min_y
    canvas = np.full((canvas_height, canvas_width, 4), 0, dtype=np.uint8)
    
    # Drawing a blue frame for the A4 paper
    orig_x_offset = -min_x
    orig_y_offset = -min_y
    cv2.rectangle(canvas, (orig_x_offset, orig_y_offset), 
                  (orig_x_offset + board_width, orig_y_offset + board_height), 
                  (255, 0, 0, 50), 4)
    
    # Putting fragments on paper with shifted coordinate system
    for p in placed_pieces:
        M = cv2.getRotationMatrix2D(p['center'], p['rot'], 1.0)
        M[0, 2] += (p['new_w'] / 2) - p['center'][0]
        M[1, 2] += (p['new_h'] / 2) - p['center'][1]
        
        rotated_piece = cv2.warpAffine(
            p['fragment'].data, M, (p['new_w'], p['new_h']), 
            flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0)
        )
        
        draw_x = p['x'] - min_x
        draw_y = p['y'] - min_y
        
        roi = canvas[draw_y : draw_y + p['new_h'], draw_x : draw_x + p['new_w']]
        alpha_mask = rotated_piece[:, :, 3] > 0
        roi[alpha_mask] = rotated_piece[alpha_mask]
        
    return canvas

def calculate_optimal_board_size(fragments, aspect_ratio=1.414, margin_multiplier=1):
    """
    Calculates the optimal paper size for the fragments.
    
    Args:
        fragments (list[ImageFragment]): List of extracted fragments.
        aspect_ratio (float): Paper sides proportions (default 1.414 - A4/A5 format)
        margin_multiplier (float): Extra space
        
    Returns:
        tuple[int, int]: Width and height of the paper in pixels.
    """
    total_area = 0
    max_piece_diagonal = 0
    
    for frag in fragments:
        # Counting pixels where Alpha > 127
        alpha_channel = frag.data[:, :, 3]
        piece_area = np.sum(alpha_channel > 127)
        total_area += piece_area
        
        # Saving the biggest diagonal (safeguard against a sheet that's too narrow)
        h, w = frag.data.shape[:2]
        diagonal = math.sqrt(w**2 + h**2)
        if diagonal > max_piece_diagonal:
            max_piece_diagonal = diagonal

    # Additional margin for space between fragments
    target_area = total_area * margin_multiplier
    
    # Calculating sides from the proporion: Area = W * H, H = W * ratio =>  W = sqrt(Area / ratio)
    width = math.sqrt(target_area / aspect_ratio)
    height = width * aspect_ratio
    
    # Safeguard: sides bigger than the biggest fragment after roattion
    width = max(width, max_piece_diagonal)
    height = max(height, max_piece_diagonal * aspect_ratio)
    
    return int(width), int(height)

def run_evolution_cluster(fragments, funkhouser=False, width=2480, height=3508):
    straightened = straighten_fragments(fragments)
    oriented_results = orient_fragments([frag for frag, _ in straightened])

    fragments = [frag for frag, _ in oriented_results]
    ocr_known = [known for _, known in oriented_results]

    # for the moment, we're using a specified width and height
    width, height = calculate_optimal_board_size(fragments)
    contour_anchors = extract_contour_anchors(fragments, ocr_known=ocr_known)
    if funkhouser:
        precompute_pairwise_matches(contour_anchors, top_k=5)
    else:
        PAIRWISE_MATCH_CACHE.clear()
    
    evaluator = FitnessEvaluator(
        fragments=fragments,
        contour_anchors=contour_anchors,
        width=width,  # A4 width at 300 DPI
        height=height # A4 height at 300 DPI
    )

    ea = EvolutionaryAlgorithm(
        objective_func=evaluator.evaluate_with_graph,
        mutation_op=mutate_path,
        crossover_op=crossover_path,
        selection_op=jaccard_tournament_selection,
        fragments=fragments,
        contour_anchors=contour_anchors,
        pop_size=150
    )

    # Training
    best_individual, best_score, _, _ = ea.train(generations=300)

    best_layout = decode_path_to_layout(best_individual, fragments, contour_anchors, width, height)
    result_matrix = render_reconstruction(
        best_chromosome=best_layout, 
        fragments=fragments, 
        board_width=width, 
        board_height=height
    )

    return result_matrix