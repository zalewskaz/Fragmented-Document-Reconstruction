import re
import cv2
import numpy as np
import pytesseract
from models import ImageFragment
from .fragment_rotation import rotate_fragment

OCR_SCALE = 2
OCR_PADDING = 20
MIN_WORD_CONFIDENCE = 60
WORD_PATTERN = re.compile(r"[A-Za-z]{3,}")

def orient_fragment(fragment: ImageFragment) -> tuple[ImageFragment, bool]:
    """
    Rotates a straightened fragment by a multiple of 90 degrees so its text is upright.

    The fragment is read with OCR (Tesseract) in all four orientations; the one where the most words
    are read with high confidence wins (see `text_score`). Upside down or sideways text gets read
    as a few low-confidence characters at most.

    The fragment has to be straightened first (see `straighten_fragment`) - only rotations by
    multiples of 90 degrees are checked.

    Args:
        fragment (ImageFragment): The straightened fragment in BGRA format, with transparent background.

    Returns:
        tuple[ImageFragment, bool]:
            - the fragment rotated so its text is upright (or the unchanged one, if no words were found),
            - whether any words were found, i.e. whether the orientation is known.
    """
    image = ocr_image(fragment)
    # turns = how many times the fragment has to be rotated by 90 degrees clockwise
    scores = [text_score(np.rot90(image, -turns)) for turns in range(4)]
    best_turns = int(np.argmax(scores))

    if scores[best_turns] == 0:
        return fragment, False
    if best_turns == 0:
        return fragment, True
    # rotate_fragment rotates counter-clockwise
    return rotate_fragment(fragment, -90 * best_turns), True

def orient_fragments(fragments: list[ImageFragment], stop_callback=None) -> list[tuple[ImageFragment, bool]]:
    """
    Orients every fragment in the list (see `orient_fragment`).

    Args:
        fragments (list[ImageFragment]): The straightened fragments.
        stop_callback (callable, optional): Function returning True if the user pressed Stop -
                                            checked before each fragment; the fragments done so far are returned.

    Returns:
        list[tuple[ImageFragment, bool]]: For each fragment: the oriented fragment and whether its orientation is known.
    """
    results = []
    for fragment in fragments:
        if stop_callback is not None and stop_callback():
            break
        results.append(orient_fragment(fragment))
    return results

def ocr_image(fragment: ImageFragment) -> np.ndarray:
    """
    Prepares the fragment for OCR: greyscale on a white background, with a white margin, enlarged.

    The documents are low-resolution scans with small letters; Tesseract reads them much better
    when they're enlarged.
    """
    data = fragment.data
    alpha = data[..., 3].astype(np.float32) / 255
    gray = cv2.cvtColor(data[..., :3], cv2.COLOR_BGR2GRAY).astype(np.float32)
    on_white = (gray * alpha + 255 * (1 - alpha)).astype(np.uint8)
    padded = cv2.copyMakeBorder(on_white, OCR_PADDING, OCR_PADDING, OCR_PADDING, OCR_PADDING,
                                cv2.BORDER_CONSTANT, value=255)
    return cv2.resize(padded, None, fx=OCR_SCALE, fy=OCR_SCALE, interpolation=cv2.INTER_CUBIC)

def text_score(image: np.ndarray) -> float:
    """
    Returns how much text OCR reads on the image: the sum of the confidences (0-100) of the words
    read with confidence at least MIN_WORD_CONFIDENCE that have at least 3 letters.
    0 if no such word was found.
    """
    data = pytesseract.image_to_data(np.ascontiguousarray(image), config="--psm 11",
                                     output_type=pytesseract.Output.DICT)
    return sum(
        float(confidence)
        for text, confidence in zip(data["text"], data["conf"])
        if float(confidence) >= MIN_WORD_CONFIDENCE and WORD_PATTERN.fullmatch(text.strip(".,;:()"))
    )
