from dataclasses import dataclass
import numpy as np

@dataclass
class ImageFragment:
    """
    Represents a single puzzle piece.
    
    Attributes:
        data (np.ndarray): The image matrix of the piece with an alpha channel.
                           Transparent background pixels have an alpha of 0.
        original_x (int): The x-coordinate of the piece's bounding box in the original image.
        original_y (int): The y-coordinate of the piece's bounding box in the original image.
        rotation (float): How many degrees (counter-clockwise) the piece was rotated compared to the original image.
    """
    data: np.ndarray
    original_x: int
    original_y: int
    rotation: float = 0.0