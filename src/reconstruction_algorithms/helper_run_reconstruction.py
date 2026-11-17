from pathlib import Path
import cv2
import sys

# fix imports
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from utils import read_image
from processing import get_fragment_contours, extract_fragments
from models import ExtractionMethod
from reconstruction_algorithms import reconstruct_unrotated_strips

if __name__=="__main__":
    path = root_dir.parent / "data/unrotated_strips/0000009966_20261117_115656.png"
    # path = root_dir.parent / "data/unrotated_strips/0000018957_20261117_115708.png"
    # path = root_dir.parent / "data/unrotated_strips/0000093958_20261117_115721.png"
    # path = root_dir.parent / "data/unrotated_strips/0000121291_20261117_115743.png"
    # path = root_dir.parent / "data/unrotated_strips/0000136298_20261117_115800.png"
    # path = root_dir.parent / "data/unrotated_strips/0000137530_20261117_115812.png"
    # path = root_dir.parent / "data/unrotated_strips/aee44c00_20261117_115827.png"
    # path = root_dir.parent / "data/unrotated_strips/avc85f00-page02_3_20261117_115841.png"
    
    # read in specified file
    image_matrix = read_image(path)    

    # extract fragments through the extracting function into a list
    extraction_mask, contour_mask = get_fragment_contours(image_matrix, ExtractionMethod.FLOOD_FILL)
    extracted_fragments = extract_fragments(image_matrix, extraction_mask)

    # pass this into pairwise matching algorithm
    result_image = reconstruct_unrotated_strips(extracted_fragments)

    # display result image
    cv2.namedWindow("Test Viewer", cv2.WINDOW_NORMAL)    
    cv2.resizeWindow("Test Viewer", 400, 600)     
    cv2.imshow("Test Viewer", result_image)
    cv2.waitKey(0) # wait indefinitely for a keystroke
    cv2.destroyAllWindows() # close the window once a key is pressed
