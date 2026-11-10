from dataclasses import dataclass
from typing import List, Optional
import numpy as np
from .parameters_enums import SplittingMethod
from .fragment import ImageFragment

@dataclass
class ProjectSession:
    """
    Stores the state and data of the current user session.

    Attributes:
        original_image (np.ndarray, optional): Original image matrix imported into the program.
        bw_image (np.ndarray, optional): Grayscaled image matrix.
        binarized_image (np.ndarray, optional): Binarized image matrix.
        mask (np.ndarray, optional): The mask representing cut lines on the image; stored as a binary matrix where 1 = cut line.
        fragments (List[ImageFragment]): List of fragments created by cutting the image, each stored as a separate BGRA image matrix with transparent background.
        pieces_on_background (np.ndarray, optional): Image matrix of fragments scattered on a solid background.
        reconstructed_image (np.ndarray, optional): Image matrix after reconstructing it using one of the algorithms.
    """

    original_image: Optional[np.ndarray] = None
    bw_image: Optional[np.ndarray] = None
    binarized_image: Optional[np.ndarray] = None
    mask: Optional[np.ndarray] = None
    fragments: List[ImageFragment] = None
    pieces_on_background: Optional[np.ndarray] = None
    reconstructed_image: Optional[np.ndarray] = None