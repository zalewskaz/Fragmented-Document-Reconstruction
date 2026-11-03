from enum import Enum

class SplittingMethod(str, Enum):
    EVEN_VERTICAL = "Even vertical strips"
    EVEN_HORIZONTAL = "Even horizontal strips"
    RANDOM_VERTICAL = "Random vertical strips"
    RANDOM_HORIZONTAL = "Random horizontal strips"
    EVEN_RECTANGLES = "Even rectangle pieces"
    RANDOM_RECTANGLES = "Random rectangle pieces"
    SEGMENTED_STRIPS = "Segmented strips"
    STRAIGHT_POLYGONS = "Straight-edge polygons"
    POLYLINE_POLYGONS = "Polyline polygons"
    VORONOI_POLYGONS = "Voronoi polygons"
    BEZIER_CURVES = "Bezier curves"

class RotationOption(str, Enum): 
    NO_ROTATION = "No rotation"
    ROTATION_RANDOM = "Rotate randomly"
    ROTATION_90DEG = "Rotate by k*90 degrees"
    ROTATION_180DEG = "Rotate by k*180 degrees"

class EdgePixelAttributionOption(str, Enum):
    DISAPPEAR = "None"
    RANDOM_ATTRIBUTION = "Random"
    NON_RANDOM_ATTRIBUTION = "Non-random"
