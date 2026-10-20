from dataclasses import dataclass
from typing import List, Optional
import numpy as np

@dataclass
class ProjectSession:
    original_image: Optional[np.ndarray] = None
    bw_image: Optional[np.ndarray] = None
    binarized_image: Optional[np.ndarray] = None
    mask: Optional[np.ndarray] = None
    # puzzle_pieces: List[PuzzlePiece] = None