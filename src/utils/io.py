from pathlib import Path
from typing import List
from datetime import datetime
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
    array_img = cv2.imdecode(np.fromfile(str(path_obj), dtype=np.uint8), cv2.IMREAD_COLOR)
            
    if array_img is None:
        raise InvalidImageInputError(f"Failed to read the first image: {path_obj.name}")
        
    return array_img

def save_image_as_png(output_dir: Path, original_file_path: Path, image: np.ndarray) -> bool:
    """
    Save an OpenCV image as a PNG with a timestamped filename.

    The output filename follows the format ``<original_filename>_<YYYYMMDD_HHMMSS>.png``.

    Raises a custom exception if openCV fails to save the file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # generate a filename in the format of: originalFileNameYYYYMMDD_HHMMSS
    original_file_name = original_file_path.stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{original_file_name}_{timestamp}.png"

    full_path = output_dir / filename

    success = cv2.imwrite(str(full_path), image)

    if not success:
        raise ImageSaveFailedError(
            f"OpenCV failed to write the image to {full_path}"
        )

    return full_path
