import cv2
import numpy as np
import pytest


@pytest.fixture
def sample_image() -> np.ndarray:
    """Return a small synthetic RGB image."""
    image = np.zeros((10, 12, 3), dtype=np.uint8)
    image[:, :] = (20, 100, 200)
    return image


@pytest.fixture
def supported_image_file(tmp_path, sample_image):
    """Create a real PNG image file in a temporary directory."""
    image_path = tmp_path / "sample.png"
    success = cv2.imwrite(str(image_path), sample_image)

    assert success, "Failed to create the test image"

    return image_path