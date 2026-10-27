from datetime import datetime as RealDateTime
from pathlib import Path
from unittest.mock import Mock

import cv2
import numpy as np
import pytest

from utils import io

# ---------------------------------------------------------------------
# get_valid_paths
# ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "extension",
    sorted(io.VALID_EXTENSIONS),
)
def test_get_valid_paths_accepts_supported_extensions(
    tmp_path, extension
):
    """Accept files with every supported extension."""
    image_path = tmp_path / f"image{extension}"
    image_path.touch()

    result = io.get_valid_paths(str(image_path))

    assert result == [image_path]


def test_get_valid_paths_is_case_insensitive(tmp_path):
    """Accept supported extensions regardless of letter case."""
    image_path = tmp_path / "image.PNG"
    image_path.touch()

    assert io.get_valid_paths(str(image_path)) == [image_path]


def test_get_valid_paths_rejects_missing_path(tmp_path):
    """Raise an exception when the path does not exist."""
    missing_path = tmp_path / "missing.png"

    with pytest.raises(
        io.InvalidImageInputError,
        match="does not exist",
    ):
        io.get_valid_paths(str(missing_path))


def test_get_valid_paths_rejects_unsupported_file(tmp_path):
    """Reject files with unsupported extensions."""
    file_path = tmp_path / "document.txt"
    file_path.touch()

    with pytest.raises(
        io.InvalidImageInputError,
        match="not a supported image format",
    ):
        io.get_valid_paths(str(file_path))


def test_get_valid_paths_returns_images_in_directory(tmp_path):
    """Return supported image files directly inside a directory."""
    image1 = tmp_path / "first.png"
    image2 = tmp_path / "second.jpg"
    unsupported = tmp_path / "notes.txt"

    image1.touch()
    image2.touch()
    unsupported.touch()

    result = io.get_valid_paths(str(tmp_path))

    assert set(result) == {image1, image2}
    assert len(result) == 2


def test_get_valid_paths_ignores_subdirectories(tmp_path):
    """Do not recursively search nested directories."""
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()

    nested_image = nested_dir / "image.png"
    nested_image.touch()

    with pytest.raises(
        io.InvalidImageInputError,
        match="contains no valid image files",
    ):
        io.get_valid_paths(str(tmp_path))


def test_get_valid_paths_rejects_empty_directory(tmp_path):
    """Raise an exception when a directory has no supported images."""
    with pytest.raises(
        io.InvalidImageInputError,
        match="contains no valid image files",
    ):
        io.get_valid_paths(str(tmp_path))


def test_get_valid_paths_ignores_directories_named_like_images(
    tmp_path,
):
    """Ignore directories with supported image extensions."""
    image_dir = tmp_path / "fake.png"
    image_dir.mkdir()

    with pytest.raises(
        io.InvalidImageInputError,
        match="contains no valid image files",
    ):
        io.get_valid_paths(str(tmp_path))



# ---------------------------------------------------------------------
# read_image
# ---------------------------------------------------------------------

def test_read_image_decodes_image(supported_image_file, sample_image):
    """Read an image file into a BGR NumPy array."""
    result = io.read_image(supported_image_file)

    assert isinstance(result, np.ndarray)
    assert result.shape == sample_image.shape
    assert result.dtype == np.uint8
    np.testing.assert_array_equal(result, sample_image)


def test_read_image_rejects_corrupted_image(tmp_path):
    """Raise an exception when the file cannot be decoded."""
    image_path = tmp_path / "corrupted.png"
    image_path.write_bytes(b"not a valid image")

    with pytest.raises(
        io.InvalidImageInputError,
        match="Failed to read",
    ):
        io.read_image(image_path)


# ---------------------------------------------------------------------
# save_image_as_png
# ---------------------------------------------------------------------

def test_save_image_creates_output_directory(
    tmp_path, sample_image
):
    """Create missing output directories and save the image."""
    output_dir = tmp_path / "new" / "images"
    original_path = Path("holiday/photo.jpg")

    result = io.save_image_as_png(
        output_dir, original_path, sample_image
    )

    assert output_dir.is_dir()
    assert result.exists()
    assert result.parent == output_dir
    assert result.name.endswith(".png")
    assert result.name.startswith("photo_")


def test_save_image_uses_expected_timestamp(
    tmp_path, sample_image, monkeypatch
):
    """Include the current timestamp in the output filename."""
    fixed_time = RealDateTime(2026, 10, 27, 12, 34, 56)

    class FixedDateTime:
        @staticmethod
        def now():
            return fixed_time

    monkeypatch.setattr(io, "datetime", FixedDateTime)

    output_dir = tmp_path / "output"
    original_path = Path("photo.jpg")

    result = io.save_image_as_png(
        output_dir, original_path, sample_image
    )

    assert result.name == "photo_20261027_123456.png"


def test_save_image_writes_valid_png(
    tmp_path, sample_image
):
    """Verify that the saved file can be decoded as an image."""
    result = io.save_image_as_png(
        tmp_path / "output",
        Path("original.jpeg"),
        sample_image,
    )

    assert result.is_file()

    decoded = cv2.imread(str(result), cv2.IMREAD_COLOR)

    assert decoded is not None
    assert decoded.shape == sample_image.shape
    np.testing.assert_array_equal(decoded, sample_image)


def test_save_image_raises_when_opencv_write_fails(
    tmp_path, sample_image, monkeypatch
):
    """Raise ImageSaveFailedError if OpenCV cannot write the image."""
    monkeypatch.setattr(io.cv2, "imwrite", Mock(return_value=False))

    output_dir = tmp_path / "output"
    original_path = Path("photo.jpg")

    with pytest.raises(
        io.ImageSaveFailedError,
        match="OpenCV failed to write",
    ):
        io.save_image_as_png(
            output_dir, original_path, sample_image
        )


def test_save_image_uses_original_filename_without_extension(
    tmp_path, sample_image, monkeypatch
):
    """Preserve the original stem when generating the filename."""
    fixed_time = RealDateTime(2026, 1, 2, 3, 4, 5)

    class FixedDateTime:
        @staticmethod
        def now():
            return fixed_time

    monkeypatch.setattr(io, "datetime", FixedDateTime)

    result = io.save_image_as_png(
        tmp_path,
        Path("my.original.photo.jpeg"),
        sample_image,
    )

    assert result.name == "my.original.photo_20260102_030405.png"
