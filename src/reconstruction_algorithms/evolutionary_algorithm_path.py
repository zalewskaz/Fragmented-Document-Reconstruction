import numpy as np
import random
from tqdm import tqdm
import math
import copy
import cv2

def _transform_point(pt, orig_w, orig_h, angle_deg):
    """
    Calculates the new (x, y) coordinates of a local point within a fragment
    after the fragment is rotated with an expanded bounding box.
    Matches the exact rotation logic used in FitnessEvaluator and render_reconstruction.
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
    
    # Step 0: Place the root anchor fragment at the origin (0, 0) initially
    root_gene = chromosome[0]
    root_idx = root_gene['frag_idx']
    root_rot = root_gene['base_rot']
    
    root_h, root_w = fragments[root_idx].data.shape[:2]
    _, root_new_w, root_new_h = _transform_point((0, 0), root_w, root_h, root_rot)
    
    layout[root_idx] = [0.0, 0.0, root_rot]
    
    # Track bounding box of the entire assembled structure
    min_x, min_y = 0.0, 0.0
    max_x, max_y = float(root_new_w), float(root_new_h)
    
    # Steps 1 .. N-1: Sequentially attach each piece to the previous piece in the path
    for step in range(1, len(chromosome)):
        prev_gene = chromosome[step - 1]
        curr_gene = chromosome[step]
        
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
            
        # p_anchor = contour_anchors[prev_idx][curr_gene['parent_anchor_idx']]
        # c_anchor = contour_anchors[curr_idx][curr_gene['child_anchor_idx']]
        
        # Calculate target rotation:
        # In OpenCV, positive angle rotates counter-clockwise, while image Y-axis points down.
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
        
        # Align child's anchor point directly onto parent's anchor point
        curr_x = parent_global_pt_x - c_rot_x
        curr_y = parent_global_pt_y - c_rot_y
        
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

class FitnessEvaluator:
    def __init__(self, fragments, contour_anchors, width, height, scale_factor=4.0, 
                 w_overlap=1000.0, w_out=1500.0, w_compact=0.5, w_edge_len=120.0, w_color_diff=0.2):
        self.fragments = fragments
        self.contour_anchors = contour_anchors
        self.scale_factor = scale_factor
        
        self.orig_width = width
        self.orig_height = height
        self.width = int(width / scale_factor)
        self.height = int(height / scale_factor)
        
        self.w_overlap = w_overlap
        self.w_out = w_out
        self.w_compact = w_compact
        self.w_edge_len = w_edge_len       # Reward per pixel of valid seam contact
        self.w_color_diff = w_color_diff   # Penalty weight applied to SUM of squared intensity differences
        
        # Use a 5x5 kernel to sample a 2-pixel band across seams (captures text & background texture better)
        self.kernel = np.ones((5, 5), np.uint8)

        # Pre-calculate downscaled binary masks AND grayscale textures for fast seam comparison
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
        h, w = arr.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        cos_val = np.abs(M[0, 0])
        sin_val = np.abs(M[0, 1])
        new_w = int((h * sin_val) + (w * cos_val))
        new_h = int((h * cos_val) + (w * sin_val))
        
        M[0, 2] += (new_w / 2) - center[0]
        M[1, 2] += (new_h / 2) - center[1]
        
        return cv2.warpAffine(arr, M, (new_w, new_h), flags=cv2.INTER_NEAREST)

    def evaluate(self, chromosome) -> float:
        layout = decode_path_to_layout(
            chromosome=chromosome,
            fragments=self.fragments,
            contour_anchors=self.contour_anchors,
            board_width=self.orig_width,
            board_height=self.orig_height
        )
        
        board = np.zeros((self.height, self.width), dtype=np.int16)
        edge_board = np.zeros((self.height, self.width), dtype=np.int16)
        gray_canvas = np.zeros((self.height, self.width), dtype=np.float32)
        
        # Store each piece's inner-border grayscale values to compare across seams
        seam_color_sum = np.zeros((self.height, self.width), dtype=np.float32)
        seam_color_sq_sum = np.zeros((self.height, self.width), dtype=np.float32)
        seam_count = np.zeros((self.height, self.width), dtype=np.int16)
        
        out_of_bounds_pixels = 0
        
        for i, gene in enumerate(layout):
            orig_x, orig_y, rot = gene
            mask = self.scaled_masks[i]
            gray = self.scaled_grays[i]
            
            rotated_mask = self._rotate_array(mask, rot)
            rotated_gray = self._rotate_array(gray, rot)
            new_h, new_w = rotated_mask.shape
            
            start_x = int(orig_x / self.scale_factor)
            start_y = int(orig_y / self.scale_factor)
            
            b_x1, b_y1 = max(0, start_x), max(0, start_y)
            b_x2, b_y2 = min(self.width, start_x + new_w), min(self.height, start_y + new_h)
            
            if b_x1 >= b_x2 or b_y1 >= b_y2:
                out_of_bounds_pixels += int(np.sum(rotated_mask))
                continue
                
            m_x1 = b_x1 - start_x
            m_y1 = b_y1 - start_y
            m_x2 = m_x1 + (b_x2 - b_x1)
            m_y2 = m_y1 + (b_y2 - b_y1)
            
            valid_mask = rotated_mask[m_y1:m_y2, m_x1:m_x2]
            valid_gray = rotated_gray[m_y1:m_y2, m_x1:m_x2].astype(np.float32)
            
            # 1-pixel outer border (just outside the piece)
            dilated = cv2.dilate(valid_mask, self.kernel, iterations=1)
            outer_border = dilated - valid_mask
            
            # Project the piece's edge grayscale value 1 pixel outward onto its outer_border
            # Using dilation on masked grayscale propagates the edge pixel intensity outward
            masked_gray = np.where(valid_mask == 1, valid_gray, 0.0)
            propagated_gray = cv2.dilate(masked_gray, self.kernel, iterations=1)
            
            if b_x1 < b_x2 and b_y1 < b_y2:
                board[b_y1:b_y2, b_x1:b_x2] += valid_mask
                edge_board[b_y1:b_y2, b_x1:b_x2] += outer_border
                
                # Accumulate edge color statistics only along the outer border
                border_bool = (outer_border == 1)
                seam_color_sum[b_y1:b_y2, b_x1:b_x2][border_bool] += propagated_gray[border_bool]
                seam_color_sq_sum[b_y1:b_y2, b_x1:b_x2][border_bool] += (propagated_gray[border_bool] ** 2)
                seam_count[b_y1:b_y2, b_x1:b_x2][border_bool] += 1
                
            pixels_on_board = int(np.sum(valid_mask))
            total_pixels = int(np.sum(rotated_mask))
            out_of_bounds_pixels += (total_pixels - pixels_on_board)

        # 1. Overlap penalty (prevents path from folding onto itself)
        overlap_pixels = int(np.sum(board[board > 1] - 1))
        
        # Metric 2: Empty gaps inside bounding box (penalizes black holes between pieces)
        active_pixels = np.where(board > 0)
        if len(active_pixels[0]) > 0:
            min_y, max_y = np.min(active_pixels[0]), np.max(active_pixels[0])
            min_x, max_x = np.min(active_pixels[1]), np.max(active_pixels[1])
            bbox_area = (max_x - min_x) * (max_y - min_y)
            filled_area = int(np.sum(board > 0))
            empty_gaps = max(0, bbox_area - filled_area)
        else:
            empty_gaps = self.width * self.height

        # 3. Contact length & Visual Seam Consistency (Sum of Squared Differences along the seam)
        seam_mask = (seam_count >= 2) & (board == 0)
        contact_length = int(np.sum(seam_mask))
        
        if contact_length > 0:
            n = seam_count[seam_mask].astype(np.float32)
            mean_val = seam_color_sum[seam_mask] / n
            mean_sq_val = seam_color_sq_sum[seam_mask] / n
            
            # Variance (squared deviation) per seam pixel: penalizes sharp white-to-gray jumps heavily
            squared_diff = np.maximum(0.0, mean_sq_val - (mean_val ** 2))
            total_color_mismatch = float(np.sum(squared_diff))
        else:
            total_color_mismatch = 1e6

        score = (self.w_overlap * overlap_pixels) + \
                (self.w_out * out_of_bounds_pixels) + \
                (self.w_compact * empty_gaps) - \
                (self.w_edge_len * contact_length) + \
                (self.w_color_diff * total_color_mismatch)
                
        return float(score)

def roulette_wheel_selection(population, scores, pop_size):
    best_idx = np.argmin(scores)
    elite_individual = population[best_idx].copy()
    elite_score = scores[best_idx]

    worst_score = np.max(scores)
    fitness = worst_score - scores + 1e-6 
    
    probabilities = fitness / np.sum(fitness)
    
    total_pool_size = len(population)
    selected_indices = np.random.choice(total_pool_size, size=pop_size-1, p=probabilities)
    
    new_population = population[selected_indices].copy()
    new_scores = scores[selected_indices].copy()

    final_population = np.vstack(([elite_individual], new_population))
    final_scores = np.append(elite_score, new_scores)
    
    return final_population, final_scores

def tournament_selection(population, scores, pop_size, k=3):
    # Ratujemy absolutnie najlepszego osobnika (Elitaryzm)
    best_idx = np.argmin(scores)
    elite_individual = copy.deepcopy(population[best_idx])
    elite_score = scores[best_idx]

    new_population = []
    new_scores = []
    
    total_pool_size = len(population)
    
    # Kręcimy turniej dla pozostałych miejsc (pop_size - 1)
    for _ in range(pop_size - 1):
        participants_idx = np.random.choice(total_pool_size, size=k, replace=False)
        winner_idx = participants_idx[np.argmin(scores[participants_idx])]
        
        new_population.append(copy.deepcopy(population[winner_idx]))
        new_scores.append(scores[winner_idx])
        
    # Sklejamy elitę z resztą wygranych
    # final_population = np.vstack(([elite_individual], new_population))
    final_population = [elite_individual] + new_population
    final_scores = np.append(elite_score, new_scores)
    
    return final_population, final_scores

def mutate_path(chromosome, contour_anchors, progress):
    """
    Mutates a path-based chromosome by either altering the sequence of pieces
    or fine-tuning the connection points and angles along the contours.
    """
    mutated = copy.deepcopy(chromosome)
    num_genes = len(mutated)
    
    # Temperature decays from 1.0 to 0.05 over generations
    temp = max(0.05, 1.0 - progress)
    
    # 1. Structural Mutation: Alter the order of fragments in the path
    if random.random() < 0.4 * temp:
        # Pick two indices (excluding index 0 if we want to keep the anchor stable, or include it)
        idx1, idx2 = random.sample(range(num_genes), 2)
        
        # Swap fragment IDs
        mutated[idx1]['frag_idx'], mutated[idx2]['frag_idx'] = (
            mutated[idx2]['frag_idx'], 
            mutated[idx1]['frag_idx']
        )
        
        # Re-validate anchor indices for affected steps and their immediate successors
        for idx in {idx1, idx2, idx1 + 1, idx2 + 1}:
            if 0 < idx < num_genes:
                prev_frag = mutated[idx - 1]['frag_idx']
                curr_frag = mutated[idx]['frag_idx']
                
                max_p = max(0, len(contour_anchors[prev_frag]) - 1)
                max_c = max(0, len(contour_anchors[curr_frag]) - 1)
                
                mutated[idx]['parent_anchor_idx'] = random.randint(0, max_p)
                mutated[idx]['child_anchor_idx'] = random.randint(0, max_c)

    # 2. Local Connection Mutation: Adjust anchor points and angle offsets
    # Mutate 1 to 3 connections per call
    num_local_mutations = random.randint(1, max(1, num_genes // 4))
    target_indices = random.sample(range(num_genes), num_local_mutations)
    
    for idx in target_indices:
        if idx == 0:
            # Mutate the root anchor's base orientation
            if random.random() < 0.3:
                mutated[0]['base_rot'] = random.choice([0.0, 90.0, 180.0, 270.0])
            else:
                mutated[0]['base_rot'] = (mutated[0]['base_rot'] + random.uniform(-15.0 * temp, 15.0 * temp)) % 360.0
        else:
            prev_frag = mutated[idx - 1]['frag_idx']
            curr_frag = mutated[idx]['frag_idx']
            
            num_p_anchors = len(contour_anchors[prev_frag])
            num_c_anchors = len(contour_anchors[curr_frag])
            
            # Shift parent anchor along the contour
            if num_p_anchors > 0:
                if random.random() < 0.2 * temp:
                    # Big jump to a completely different edge
                    mutated[idx]['parent_anchor_idx'] = random.randint(0, num_p_anchors - 1)
                else:
                    # Slide along the current edge
                    step_shift = int(random.gauss(0, max(1, int(num_p_anchors * 0.1 * temp))))
                    mutated[idx]['parent_anchor_idx'] = (mutated[idx]['parent_anchor_idx'] + step_shift) % num_p_anchors

            # Shift child anchor along the contour
            if num_c_anchors > 0:
                if random.random() < 0.2 * temp:
                    mutated[idx]['child_anchor_idx'] = random.randint(0, num_c_anchors - 1)
                else:
                    step_shift = int(random.gauss(0, max(1, int(num_c_anchors * 0.1 * temp))))
                    mutated[idx]['child_anchor_idx'] = (mutated[idx]['child_anchor_idx'] + step_shift) % num_c_anchors

            # Fine-tune the angle offset (keep edges nearly parallel)
            mutated[idx]['angle_offset'] += random.uniform(-1.5 * temp, 1.5 * temp)
            mutated[idx]['angle_offset'] = max(-2.5, min(2.5, mutated[idx]['angle_offset']))

    return mutated

def crossover_path(parent1, parent2, contour_anchors):
    """
    Performs Order Crossover (OX) adapted for path-based chromosomes.
    Preserves valid sub-paths and repairs connection anchors at slice boundaries.
    """
    def _build_child(p1, p2):
        size = len(p1)
        start, end = sorted(random.sample(range(size), 2))
        
        child = [None] * size
        used_frags = set()
        
        # 1. Copy the slice from parent1
        for i in range(start, end + 1):
            child[i] = copy.deepcopy(p1[i])
            used_frags.add(p1[i]['frag_idx'])
            
        # 2. Fill remaining positions with unused fragments in the order they appear in parent2
        p2_remaining = [gene for gene in p2 if gene['frag_idx'] not in used_frags]
        p2_idx = 0
        
        for i in range(size):
            if child[i] is None:
                source_gene = p2_remaining[p2_idx]
                p2_idx += 1
                
                frag_id = source_gene['frag_idx']
                
                if i == 0:
                    # Construct root anchor gene
                    base_rot = source_gene.get('base_rot', random.choice([0.0, 90.0, 180.0, 270.0]))
                    child[i] = {
                        'frag_idx': frag_id,
                        'base_rot': base_rot
                    }
                else:
                    # Construct connection gene
                    prev_frag_id = child[i - 1]['frag_idx']
                    max_p = max(0, len(contour_anchors[prev_frag_id]) - 1)
                    max_c = max(0, len(contour_anchors[frag_id]) - 1)
                    
                    # Preserve child_anchor_idx if valid, otherwise randomize
                    c_anchor = source_gene.get('child_anchor_idx', 0)
                    if c_anchor > max_c:
                        c_anchor = random.randint(0, max_c)
                        
                    child[i] = {
                        'frag_idx': frag_id,
                        'parent_anchor_idx': random.randint(0, max_p),
                        'child_anchor_idx': c_anchor,
                        'angle_offset': source_gene.get('angle_offset', 0.0)
                    }
                    
        # 3. Repair both slice boundaries (at index `start` and `end + 1`)
        for boundary_idx in (start, end + 1):
            if 0 < boundary_idx < size:
                prev_frag_id = child[boundary_idx - 1]['frag_idx']
                curr_frag_id = child[boundary_idx]['frag_idx']
                max_p = max(0, len(contour_anchors[prev_frag_id]) - 1)
                max_c = max(0, len(contour_anchors[curr_frag_id]) - 1)
                
                child[boundary_idx]['parent_anchor_idx'] = random.randint(0, max_p)
                child[boundary_idx]['child_anchor_idx'] = random.randint(0, max_c)

        # 4. Ensure index 0 has the root schema (in case start == 0 was copied without base_rot or vice versa)
        if 'base_rot' not in child[0]:
            child[0] = {
                'frag_idx': child[0]['frag_idx'],
                'base_rot': random.choice([0.0, 90.0, 180.0, 270.0])
            }
            
        return child

    child1 = _build_child(parent1, parent2)
    child2 = _build_child(parent2, parent1)
    
    return child1, child2

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

        # Inicjalizacja populacji ścieżek
        self.population = self._initialize_population()

    def _initialize_population(self):
        """
        Generuje populację losowych ścieżek łączących wszystkie fragmenty.
        """
        population = []
        
        for _ in range(self.pop_size):
            # Losujemy kolejność, w jakiej ścieżka odwiedzi kawałki (permutacja bez powtórzeń)
            order = list(range(self.num_fragments))
            random.shuffle(order)
            
            chromosome = []
            
            # KROK 0: Kotwica (pierwszy element ścieżki)
            first_frag = order[0]
            chromosome.append({
                'frag_idx': first_frag,
                'base_rot': random.choice([0.0, 90.0, 180.0, 270.0]) # Startowa orientacja całego dokumentu
            })
            
            # KROKI 1 .. N-1: Kolejne ogniwa ścieżki
            for step in range(1, self.num_fragments):
                prev_frag = order[step - 1]
                curr_frag = order[step]
                
                num_prev_anchors = len(self.contour_anchors[prev_frag])
                num_curr_anchors = len(self.contour_anchors[curr_frag])
                
                # Losujemy dowolny punkt styku na poprzednim kawałku i na nowym kawałku
                parent_anchor = random.randint(0, max(0, num_prev_anchors - 1))
                child_anchor = random.randint(0, max(0, num_curr_anchors - 1))
                
                chromosome.append({
                    'frag_idx': curr_frag,
                    'parent_anchor_idx': parent_anchor,
                    'child_anchor_idx': child_anchor,
                    'angle_offset': random.uniform(-5.0, 5.0) # Mały luz na dopasowanie krzywizny
                })
                
            population.append(chromosome)
            
        return population
        
    def train(self, generations=1000):
        scores = np.array([self.objective_func(ind) for ind in tqdm(self.population, desc="Initialization")])
        history_best = []
        history_all = []

        # iterations as the stopping point
        pbar = tqdm(range(generations), desc="Evolution")
        for gen in pbar:
            progress = gen / generations
            children = []

            # CROSSOVER
            # random pairing
            indices = np.arange(self.pop_size)
            np.random.shuffle(indices)

            for i in range(0, self.pop_size - 1, 2):
                parent1 = self.population[indices[i]]
                parent2 = self.population[indices[i+1]]
                
                if np.random.rand() < self.crossover_prob:
                    child1, child2 = self.crossover_op(parent1, parent2, self.contour_anchors)
                else:
                    child1, child2 = parent1.copy(), parent2.copy()
                    
                children.extend([child1, child2])

            # MUTATION
            mutated_children = []
            for child in children:
                if np.random.rand() < self.mutation_prob:
                    mutated_children.append(self.mutation_op(child, self.contour_anchors, progress))
                else:
                    mutated_children.append(child)
            
            # mutated_children = np.array(mutated_children)

            # EWALUATION
            children_scores = np.array([self.objective_func(c) for c in mutated_children])

            # SELECTION
            # combined_population = np.vstack((self.population, mutated_children))
            combined_population = self.population + mutated_children
            combined_scores = np.concatenate((scores, children_scores))
            self.population, scores = self.selection_op(combined_population, combined_scores, self.pop_size)

            best_current_score = np.min(scores)
            avg_current_score = np.mean(scores)

            pbar.set_postfix({"best_score": round(best_current_score, 2)})
            
            history_best.append(best_current_score)
            history_all.append(scores.copy())
        
        best_idx = np.argmin(scores)
        best_individual = self.population[best_idx]
        best_score = scores[best_idx]
        
        return best_individual, best_score, history_best, history_all

def render_reconstruction(best_chromosome, fragments, board_width, board_height):
    # KROK 1: Znalezienie globalnych granic (bounding box) wszystkich elementów
    # Zaczynamy od (0,0) do (board_width, board_height), aby na pewno ująć też oryginalne pole
    min_x, min_y = 0, 0 
    max_x, max_y = board_width, board_height 
    
    placed_pieces = []
    
    for i, gene in enumerate(best_chromosome):
        x, y, rot = gene
        fragment = fragments[i]
        
        # Wyliczenia rotacji, tak jak wcześniej
        h, w = fragment.data.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, rot, 1.0)
        
        cos_val = np.abs(M[0, 0])
        sin_val = np.abs(M[0, 1])
        new_w = int((h * sin_val) + (w * cos_val))
        new_h = int((h * cos_val) + (w * sin_val))
        
        start_x = int(x)
        start_y = int(y)
        
        # Aktualizacja skrajnych punktów (mogą być ujemne, jeśli fragment uciekł w lewo/górę)
        min_x = min(min_x, start_x)
        min_y = min(min_y, start_y)
        max_x = max(max_x, start_x + new_w)
        max_y = max(max_y, start_y + new_h)
        
        placed_pieces.append({
            'fragment': fragment, 'x': start_x, 'y': start_y, 'rot': rot,
            'new_w': new_w, 'new_h': new_h, 'center': center
        })
        
    # KROK 2: Utworzenie powiększonego, dynamicznego płótna
    canvas_width = max_x - min_x
    canvas_height = max_y - min_y
    canvas = np.full((canvas_height, canvas_width, 4), 0, dtype=np.uint8)
    
    # Opcjonalnie: Rysowanie półprzezroczystej ramki pokazującej docelowe "idealne" płótno
    orig_x_offset = -min_x
    orig_y_offset = -min_y
    cv2.rectangle(canvas, (orig_x_offset, orig_y_offset), 
                  (orig_x_offset + board_width, orig_y_offset + board_height), 
                  (255, 0, 0, 50), 4) # Niebieska ramka
    
    # KROK 3: Nanoszenie fragmentów z przesunięciem układu współrzędnych
    for p in placed_pieces:
        M = cv2.getRotationMatrix2D(p['center'], p['rot'], 1.0)
        M[0, 2] += (p['new_w'] / 2) - p['center'][0]
        M[1, 2] += (p['new_h'] / 2) - p['center'][1]
        
        rotated_piece = cv2.warpAffine(
            p['fragment'].data, M, (p['new_w'], p['new_h']), 
            flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0)
        )
        
        # Przesuwamy pozycję o offset wynikający z ujemnych granic
        draw_x = p['x'] - min_x
        draw_y = p['y'] - min_y
        
        # Mając nowy bounding box, mamy pewność, że nic nie wyjdzie poza zakres "canvas"
        roi = canvas[draw_y : draw_y + p['new_h'], draw_x : draw_x + p['new_w']]
        alpha_mask = rotated_piece[:, :, 3] > 0
        roi[alpha_mask] = rotated_piece[alpha_mask]
        
    return canvas

def calculate_optimal_board_size(fragments, aspect_ratio=1.414, margin_multiplier=1.1):
    """
    Oblicza optymalny rozmiar kartki do ułożenia fragmentów.
    
    Args:
        fragments (list[ImageFragment]): Lista wyciętych fragmentów.
        aspect_ratio (float): Proporcje boków kartki (domyślnie 1.414, czyli format A4/A5).
        margin_multiplier (float): Zapas miejsca (1.3 to 30% dodatkowej przestrzeni na luki).
        
    Returns:
        tuple[int, int]: Zwraca (szerokość, wysokość) w pikselach.
    """
    total_area = 0
    max_piece_diagonal = 0
    
    for frag in fragments:
        # Zliczamy tylko faktyczny obszar kawałka (piksele, gdzie Alpha > 127)
        alpha_channel = frag.data[:, :, 3]
        piece_area = np.sum(alpha_channel > 127)
        total_area += piece_area
        
        # Zapisujemy największą przekątną (zabezpieczenie, by kartka nie była za wąska)
        h, w = frag.data.shape[:2]
        diagonal = math.sqrt(w**2 + h**2)
        if diagonal > max_piece_diagonal:
            max_piece_diagonal = diagonal

    # Dodajemy margines na puste przestrzenie między kawałkami
    target_area = total_area * margin_multiplier
    
    # Wyliczamy boki na podstawie proporcji: Area = W * H, a H = W * ratio
    # Więc: Area = W * (W * ratio) = W^2 * ratio  =>  W = sqrt(Area / ratio)
    width = math.sqrt(target_area / aspect_ratio)
    height = width * aspect_ratio
    
    # Zabezpieczenie: boki muszą być co najmniej tak duże jak największy kawałek po obrocie
    width = max(width, max_piece_diagonal)
    height = max(height, max_piece_diagonal * aspect_ratio)
    
    return int(width), int(height)

def extract_contour_anchors(fragments, step_px=25, min_edge_len=40):
    """
    Extracts anchor points exclusively along straight/smooth edge segments,
    avoiding sharp corners so pieces attach edge-to-edge rather than tip-to-tip.
    """
    all_fragments_anchors = []
    
    for frag in fragments:
        alpha = frag.data[:, :, 3]
        binary_mask = (alpha > 127).astype(np.uint8)
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        
        if not contours:
            all_fragments_anchors.append([])
            continue
            
        main_contour = max(contours, key=cv2.contourArea)
        
        # Approximate contour with polygon to find actual edges (sides)
        epsilon = 0.015 * cv2.arcLength(main_contour, True)
        poly = cv2.approxPolyDP(main_contour, epsilon, True).reshape(-1, 2)
        num_vertices = len(poly)
        
        anchors = []
        for i in range(num_vertices):
            p1 = poly[i].astype(float)
            p2 = poly[(i + 1) % num_vertices].astype(float)
            
            edge_vec = p2 - p1
            edge_len = np.linalg.norm(edge_vec)
            
            if edge_len < min_edge_len:
                continue
                
            tangent_angle = math.degrees(math.atan2(edge_vec[1], edge_vec[0]))
            
            # Sample points along the middle 70% of this edge (skipping corners)
            num_samples = max(1, int((edge_len * 0.7) // step_px))
            for s in range(num_samples):
                t = 0.15 + 0.7 * ((s + 0.5) / num_samples)
                pt = p1 + t * edge_vec
                anchors.append({
                    'pt': (float(pt[0]), float(pt[1])),
                    'angle': tangent_angle,
                    'edge_len': float(edge_len)
                })
                
        all_fragments_anchors.append(anchors)
        
    return all_fragments_anchors

def run_evolution_path(fragments, width=2480, height=3508):
    # for the moment, we're using a specified width and height
    width, height = calculate_optimal_board_size(fragments)
    contour_anchors = extract_contour_anchors(fragments)
    
    evaluator = FitnessEvaluator(
        fragments=fragments,
        contour_anchors=contour_anchors,
        width=width,  # A4 width at 300 DPI
        height=height # A4 height at 300 DPI
    )

    ea = EvolutionaryAlgorithm(
        objective_func=evaluator.evaluate,
        mutation_op=mutate_path,
        crossover_op=crossover_path,
        selection_op=tournament_selection,
        fragments=fragments,
        contour_anchors=contour_anchors
    )

    # Training
    best_individual, best_score, _, _ = ea.train(generations=1000)

    best_layout = decode_path_to_layout(best_individual, fragments, contour_anchors, width, height)
    result_matrix = render_reconstruction(
        best_chromosome=best_layout, 
        fragments=fragments, 
        board_width=width, 
        board_height=height
    )

    return result_matrix