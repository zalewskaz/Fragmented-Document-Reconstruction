from enum import Enum

class SplittingMethod(str, Enum):
    """
    Defines the available algorithms for document fragmentation.

    Attributes:
        EVEN_VERTICAL: Cuts the document into vertical strips of equal width.
        EVEN_HORIZONTAL: Cuts the document into horizontal strips of equal height.
        RANDOM_VERTICAL: Cuts the document into vertical strips of random width.
        RANDOM_HORIZONTAL: Cuts the document into horizontal strips of random height.
        EVEN_RECTANGLES: Divides the document into even rectangular grids.
        RANDOM_RECTANGLES: Divides the document into randomized rectangular grids.
        SEGMENTED_STRIPS: Cuts the document into strips and then segments them further.
        STRAIGHT_POLYGONS: Divides the document into straight-edge polygons.
        POLYLINE_POLYGONS: Slices the document using randomized straight-edge polylines.
        VORONOI_POLYGONS: Fragments the document into polygonal cells using Voronoi tessellation.
        BEZIER_CURVES: Fragments the document into shapes using Bezier curves.
    """

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
    """
    Defines the available options for rotating the fragments.

    Attributes:
        NO_ROTATION: Does not apply any rotation to the fragments.
        ROTATION_RANDOM: Rotates each fragment individually by a unique, random angle.
        ROTATION_90DEG: Rotates each fragment by a multiple of 90 degrees (0, 90, 180, or 270).
        ROTATION_180DEG: Rotates each fragment randomly by a multiple of 180 degrees.
    """

    NO_ROTATION = "No rotation"
    ROTATION_RANDOM = "Rotate randomly"
    ROTATION_90DEG = "Rotate by k*90 degrees"
    ROTATION_180DEG = "Rotate by k*180 degrees"

class EdgePixelAttributionOption(str, Enum):
    """
    Defines the attribution of pixels on the cut lines.

    Attributes:
        DISAPPEAR: The pixels on the cut lines are not attributed to any fragment.
        RANDOM_ATTRIBUTION: Each pixel on the cut line is attributed to one of the fragment connected to the line.
        NON_RANDOM_ATTRIBUTION: Pixels on the cut lines are attributed to the fragments with a smaller index.
    """

    DISAPPEAR = "None"
    RANDOM_ATTRIBUTION = "Random"
    NON_RANDOM_ATTRIBUTION = "Non-random"
