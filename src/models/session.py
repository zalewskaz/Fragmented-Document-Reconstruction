from dataclasses import dataclass
from typing import List, Optional
import numpy as np
from .parameters_enums import SplittingMethod
from .fragment import ImageFragment

@dataclass
class ProjectSession:
    original_image: Optional[np.ndarray] = None
    bw_image: Optional[np.ndarray] = None
    binarized_image: Optional[np.ndarray] = None
    mask: Optional[np.ndarray] = None
    fragments: List[ImageFragment] = None
    splitting_method: Optional[SplittingMethod] = None