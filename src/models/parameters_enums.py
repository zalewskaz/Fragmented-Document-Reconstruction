from enum import Enum

class SplittingMethod(str, Enum):
    EVEN_VERTICAL = "Even vertical strips"
    EVEN_HORIZONTAL = "Even horizontal strips"
    RANDOM_VERTICAL = "Random vertical strips"
    RANDOM_HORIZONTAL = "Random horizontal strips"
    EVEN_RECTANGLES = "Even rectangle pieces"
    RANDOM_RECTANGLES = "Random rectangle pieces"
    SEGMENTED_STRIPS = "Segmented strips"