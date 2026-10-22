from pathlib import Path
from typing import List
import cv2
import numpy as np

class InvalidImageInputError(Exception):
    """Custom exception raised when file/folder input is invalid."""
    pass

class ImageSaveFailedError(Exception):
    """Custom exception raised when OpenCV fails to save the final image."""
    pass

VALID_EXTENSIONS = {
    ".jpg", ".jpeg", ".jpe", ".png", ".webp", ".bmp", ".dib", ".tiff", ".tif", ".jp2", ".pbm", ".pgm", ".ppm", ".pxm", ".pnm",".exr", ".hdr", ".pic",".sr", ".ras"
}

def get_valid_paths(path_str: str) -> List[Path]:
    """
    Validates a file or directory and returns a list of valid image paths.
    Raises a custom exception if the path doesn't lead to any valid image files. 
    Does not load images into memory.
    """
    path = Path(path_str)
    
    if not path.exists():
        raise InvalidImageInputError(f"The path does not exist: {path}")

    valid_paths = []

    # single file
    if path.is_file():
        if path.suffix.lower() not in VALID_EXTENSIONS:
            raise InvalidImageInputError("The selected file is not a supported image format.")
        valid_paths.append(path)

    # directory
    elif path.is_dir():
        for file_path in path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in VALID_EXTENSIONS:
                valid_paths.append(file_path)
                
        if not valid_paths:
            raise InvalidImageInputError("The selected folder contains no valid image files.")
    
    return valid_paths

def read_image(path_obj: Path) -> np.ndarray:
    # array_img = cv2.imread(str(path_obj))
    # loads images from paths with characters out of ASCII range
    array_img = cv2.imdecode(np.fromfile(str(path_obj), dtype=np.uint8), cv2.IMREAD_COLOR)
            
    if array_img is None:
        raise InvalidImageInputError(f"Failed to read the first image: {path_obj.name}")
        
    return array_img

# session class object should contain: a list of all valid paths, and *only* the ndarray for current image
# to avoid processing 500 files at once and thus destroying memory usage
# potentially also bool is_batch, automatically based on number of valid paths
# but maybe unnecessary since we will just repeat the exact same process for all path files, regarless of whether we have 1 or many

def save_image_as_png(output_dir: str, original_filename: str, image: np.ndarray) -> bool:
    # moze tu jeszcze zmienie zeby bralo path a nie str
    """
    Saves an OpenCV ndarray image to the specified directory strictly as a PNG.
    Creates the directory if it does not already exist.
    """
    dir_path = Path(output_dir)
    dir_path.mkdir(parents=True, exist_ok=True)
    
    # change extension to png
    safe_filename = f"{Path(original_filename).stem}.png"
    
    full_path = dir_path / safe_filename
    
    # cv2.imwrite automatically writes to png bc its written in filename
    success = cv2.imwrite(str(full_path), image)
    
    if not success:
        raise ImageSaveFailedError(f"Error: OpenCV failed to write the image to {full_path}")
        
    return success
