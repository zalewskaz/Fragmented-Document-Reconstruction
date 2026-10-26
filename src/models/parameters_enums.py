from enum import Enum

class SplittingMethod(str, Enum):
    EVEN_VERTICAL = "Even vertical stripes"
    EVEN_HORIZONTAL = "Even horizontal stripes"
    RANDOM_VERTICAL = "Random vertical stripes"
    RANDOM_HORIZONTAL = "Random horizontal stripes"