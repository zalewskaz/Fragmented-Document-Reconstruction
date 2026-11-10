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
    Validates a file or directory path and resolves all supported image files within it.

    If a single file path is provided, it verifies the extension. If a directory 
    is provided, it scans the directory for all files matching supported image 
    extensions. 

    Args:
        path_str (str): The string representation of the file or directory path to check.

    Returns:
        List[Path]: A list of pathlib.Path objects pointing to valid image files.

    Raises:
        InvalidImageInputError: If the path does not exist, if a single file has an 
        unsupported extension, or if a directory contains no supported image files.
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
    """
    Reads an image from the filesystem into a NumPy array. 

    Args:
        path_obj (Path): The pathlib.Path object pointing to the image file.

    Returns:
        np.ndarray: A 4-channel (BGR) NumPy array representing the loaded image.

    Raises:
        InvalidImageInputError: If the file cannot be read or decoded into an image array.
    """
    
    array_img = cv2.imdecode(np.fromfile(str(path_obj), dtype=np.uint8), cv2.IMREAD_COLOR)
            
    if array_img is None:
        raise InvalidImageInputError(f"Failed to read the first image: {path_obj.name}")

    array_img = cv2.cvtColor(array_img, cv2.COLOR_BGR2BGRA)
        
    return array_img

def save_image_as_png(output_dir: Path, original_file_path: Path, image: np.ndarray) -> Path:
    """
    Saves an OpenCV image matrix to the filesystem as a PNG file with a timestamp.

    The output filename follows the format ``<original_filename>_<YYYYMMDD_HHMMSS>.png``.

    Args:
        output_dir (Path): The target directory where the image will be saved.
        original_file_path (Path): The path of the source image, used to derive 
            the base filename.
        image (np.ndarray): The OpenCV image array to write to disk.

    Returns:
        Path: The absolute path to the newly saved PNG file.

    Raises:
        ImageSaveFailedError: If OpenCV fails to encode or write the image to the 
        specified destination.
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
