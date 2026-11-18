import numpy as np
import random
from tqdm import tqdm
import math

import numpy as np
import cv2

class FitnessEvaluator:
    def __init__(self, fragments, width, height, scale_factor=4.0, 
                 w_overlap=1000.0, w_out=2000.0, w_compact=0.1, w_edge=50.0):
        self.scale_factor = scale_factor
        self.width = int(width / scale_factor)
        self.height = int(height / scale_factor)
        
        self.w_overlap = w_overlap
        self.w_out = w_out
        self.w_compact = w_compact
        self.w_edge = w_edge
        
        self.kernel = np.ones((3, 3), np.uint8)

        # Wracamy do ultraszybkich, jednokanałowych masek binarnych
        self.scaled_masks = []
        for frag in fragments:
            alpha = frag.data[:, :, 3]
            binary_mask = (alpha > 127).astype(np.uint8)
            new_size = (max(1, int(binary_mask.shape[1] / scale_factor)), 
                        max(1, int(binary_mask.shape[0] / scale_factor)))
            
            scaled_mask = cv2.resize(binary_mask, new_size, interpolation=cv2.INTER_NEAREST)
            self.scaled_masks.append(scaled_mask)

    def rotate_mask(self, mask: np.ndarray, angle: float) -> np.ndarray:
        h, w = mask.shape
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        cos_val = np.abs(M[0, 0])
        sin_val = np.abs(M[0, 1])
        new_w = int((h * sin_val) + (w * cos_val))
        new_h = int((h * cos_val) + (w * sin_val))
        
        M[0, 2] += (new_w / 2) - center[0]
        M[1, 2] += (new_h / 2) - center[1]
        
        return cv2.warpAffine(mask, M, (new_w, new_h), flags=cv2.INTER_NEAREST)

    def evaluate(self, chromosome) -> float:
        # Tylko dwie szybkie tablice 2D (ciała fragmentów i ich obwódki)
        board = np.zeros((self.height, self.width), dtype=np.int16)
        edge_board = np.zeros((self.height, self.width), dtype=np.int16)
        out_of_bounds_pixels = 0
        
        for i, gene in enumerate(chromosome):
            rot = gene[2]
            mask = self.scaled_masks[i]
            rotated_mask = self.rotate_mask(mask, rot)
            new_h, new_w = rotated_mask.shape
            
            orig_x, orig_y = gene[0], gene[1]
            start_x = int(orig_x / self.scale_factor)
            start_y = int(orig_y / self.scale_factor)
            
            b_x1, b_y1 = max(0, start_x), max(0, start_y)
            b_x2, b_y2 = min(self.width, start_x + new_w), min(self.height, start_y + new_h)
            
            if b_x1 >= b_x2 or b_y1 >= b_y2:
                out_of_bounds_pixels += (new_w * new_h)
                continue
                
            m_x1 = b_x1 - start_x
            m_y1 = b_y1 - start_y
            m_x2 = m_x1 + (b_x2 - b_x1)
            m_y2 = m_y1 + (b_y2 - b_y1)
            
            valid_mask = rotated_mask[m_y1:m_y2, m_x1:m_x2]
            
            # Tworzymy samą obwódkę fragmentu (krawędź)
            dilated = cv2.dilate(valid_mask, self.kernel, iterations=1)
            border = dilated - valid_mask
            
            if b_x1 < b_x2 and b_y1 < b_y2:
                board[b_y1:b_y2, b_x1:b_x2] += valid_mask
                edge_board[b_y1:b_y2, b_x1:b_x2] += border
                
            pixels_on_board = np.sum(valid_mask)
            total_pixels = np.sum(rotated_mask)
            out_of_bounds_pixels += (total_pixels - pixels_on_board)

        # 1. Kary za nałożenie i wyjście poza papier
        overlap_pixels = np.sum(board[board > 1] - 1)
        
        # 2. Kara za wielkość stosu (Compactness)
        active_pixels = np.where(board > 0)
        if len(active_pixels[0]) > 0:
            min_y, max_y = np.min(active_pixels[0]), np.max(active_pixels[0])
            min_x, max_x = np.min(active_pixels[1]), np.max(active_pixels[1])
            compactness_area = (max_x - min_x) * (max_y - min_y)
        else:
            compactness_area = self.width * self.height

        # 3. NAGRODA za Zazębianie (Edge Lock)
        # Nagradzamy miejsca, w których obwódki co najmniej 2 elementów na siebie nachodzą (edge_board >= 2),
        # ale same fragmenty się NIE nakładają (board == 0).
        touching_edges = np.sum((edge_board >= 2) & (board == 0))

        # Złożenie punktacji. Odjęcie w_edge * touching_edges wymusza na algorytmie ściskanie elementów.
        score = (self.w_overlap * overlap_pixels) + \
                (self.w_out * out_of_bounds_pixels) + \
                (self.w_compact * compactness_area) - \
                (self.w_edge * touching_edges) 
                
        return score

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
    elite_individual = population[best_idx].copy()
    elite_score = scores[best_idx]

    new_population = []
    new_scores = []
    
    total_pool_size = len(population)
    
    # Kręcimy turniej dla pozostałych miejsc (pop_size - 1)
    for _ in range(pop_size - 1):
        participants_idx = np.random.choice(total_pool_size, size=k, replace=False)
        winner_idx = participants_idx[np.argmin(scores[participants_idx])]
        
        new_population.append(population[winner_idx].copy())
        new_scores.append(scores[winner_idx])
        
    # Sklejamy elitę z resztą wygranych
    final_population = np.vstack(([elite_individual], new_population))
    final_scores = np.append(elite_score, new_scores)
    
    return final_population, final_scores

def mutation(chromosome, height, width, progress):
    mutated_chromosome = [gene.copy() for gene in chromosome]
    
    # Wybieramy od 1 do 1/3 genów do mutacji
    num_mutations = random.randint(1, max(1, len(chromosome) // 3))
    indices_to_mutate = random.sample(range(len(chromosome)), num_mutations)
    
    # TEMPERATURA: spada z 1.0 do 0.01 w miarę postępu generacji
    temp = max(0.01, 1.0 - progress)
    
    for idx in indices_to_mutate:
        x, y, rot = mutated_chromosome[idx]
        
        # Mutacja pozycji ze skalowaniem (temp)
        rand = random.randint(0, 100)
        if rand < 5:
            x = random.uniform(0, width)
            y = random.uniform(0, height)
        elif rand < 40:
            x += random.uniform(-400 * temp, 400 * temp)
            y += random.uniform(-400 * temp, 400 * temp)
        elif rand < 90:
            x += random.uniform(-30 * temp, 30 * temp)
            y += random.uniform(-30 * temp, 30 * temp)

        # Mutacja rotacji
        rand = random.randint(0, 100)
        if rand < 15:
            rot = random.uniform(0.0, 360.0)
        elif rand < 80:
            # Drobne poprawki kąta wygasające z czasem
            rot += random.uniform(-20 * temp, 20 * temp) 
            
        x = np.clip(x, -width*0.2, width*1.2)
        y = np.clip(y, -height*0.2, height*1.2)
        rot = rot % 360
            
        mutated_chromosome[idx] = [x, y, rot]
        
    return mutated_chromosome

def crossover(parent1, parent2):
    child1 = np.copy(parent1)
    child2 = np.copy(parent2)
    
    # For each fragment, 50% chance to swap it between parents
    for i in range(len(parent1)):
        if np.random.rand() < 0.5:
            child1[i], child2[i] = child2[i].copy(), child1[i].copy()
            
    return child1, child2

class EvolutionaryAlgorithm:
    def __init__(self, objective_func, mutation_op, crossover_op, selection_op, fragments, height, width, 
                 pop_size=100, crossover_prob=0.8, mutation_prob=0.25):
        self.objective_func = objective_func
        self.mutation_op = mutation_op
        self.crossover_op = crossover_op
        self.selection_op = selection_op

        self.height = height
        self.width = width

        self.fragments = fragments
        self.pop_size = pop_size
        self.chromosome_length = len(fragments)

        self.crossover_prob = crossover_prob
        self.mutation_prob = mutation_prob

        # Initialization
        self.population = self._initialize_population()

    def _initialize_population(self):
        population = []
        
        cols = int(math.ceil(math.sqrt(len(self.fragments))))
        rows = int(math.ceil(len(self.fragments) / cols))
        
        # Bezpieczna strefa (środkowe 50% planszy)
        safe_w = self.width * 0.5
        safe_h = self.height * 0.5
        offset_x = self.width * 0.25
        offset_y = self.height * 0.25
        
        cell_width = safe_w / max(1, cols)
        cell_height = safe_h / max(1, rows)

        for _ in range(self.pop_size):
            chromosome = []
            
            for idx, frag in enumerate(self.fragments):
                grid_x = (idx % cols) * cell_width
                grid_y = (idx // cols) * cell_height
                
                # Dodawanie offsetu, aby startowały bliżej środka
                x = offset_x + grid_x + random.uniform(0, cell_width * 0.5)
                y = offset_y + grid_y + random.uniform(0, cell_height * 0.5)
                
                rot = random.uniform(0.0, 360.0)
                chromosome.append([x, y, rot])
                
            population.append(chromosome)
            
        return np.array(population)
        
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
                    child1, child2 = self.crossover_op(parent1, parent2)
                else:
                    child1, child2 = parent1.copy(), parent2.copy()
                    
                children.extend([child1, child2])

            # MUTATION
            mutated_children = []
            for child in children:
                if np.random.rand() < self.mutation_prob:
                    mutated_children.append(self.mutation_op(child, self.height, self.width, progress))
                else:
                    mutated_children.append(child)
            
            mutated_children = np.array(mutated_children)

            # EWALUATION
            children_scores = np.array([self.objective_func(c) for c in mutated_children])

            # SELECTION
            combined_population = np.vstack((self.population, mutated_children))
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

def calculate_optimal_board_size(fragments, aspect_ratio=1.414, margin_multiplier=1.2):
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

def run_evolution(fragments, width=2480, height=3508):
    # for the moment, we're using a specified width and height
    width, height = calculate_optimal_board_size(fragments)
    
    evaluator = FitnessEvaluator(
        fragments=fragments,
        width=width,  # A4 width at 300 DPI
        height=height, # A4 height at 300 DPI
        w_overlap=1000.0,  # Massive penalty for overlapping
        w_out=2000.0,      # Massive penalty for falling off the page
        w_compact=0.1,      # Small incentive to pack tightly together
        w_edge=500
    )

    ea = EvolutionaryAlgorithm(
        objective_func=evaluator.evaluate,
        mutation_op=mutation,
        crossover_op=crossover,
        selection_op=tournament_selection,
        fragments=fragments,
        width=width,
        height=height
    )

    # Training
    best_individual, best_score, _, _ = ea.train(generations=2000)
                                                            
    result_matrix = render_reconstruction(
        best_chromosome=best_individual, 
        fragments=fragments, 
        board_width=width, 
        board_height=height
    )

    return result_matrix