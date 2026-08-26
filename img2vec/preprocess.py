"""Turn any logo file into the black-on-white bitmap that potrace expects."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

DEFAULT_MIN_SIZE = 0
OPAQUE_CUTOFF = 250
MIN_TRANSPARENT_FRACTION = 0.05
MID_GREY = 128
CORNER_FRACTION = 0.05
SMALLEST_CORNER = 2
DIRECTLY_USABLE_MODES = ("L", "LA", "RGB", "RGBA")


@dataclass(frozen=True)
class Mask:
    """Greyscale pixels in which the dark areas are the artwork to be traced."""

    pixels: np.ndarray
    width: int
    height: int
    scale: float


def load_image(path: Path) -> Image.Image:
    """Read an image file, honouring the orientation a camera may have recorded."""
    with Image.open(path) as opened:
        opened.load()
        return ImageOps.exif_transpose(opened)


def build_mask(image: Image.Image, *, invert: bool = False, min_size: int = DEFAULT_MIN_SIZE) -> Mask:
    """Decide what counts as artwork and return it as dark pixels on a light field."""
    if image.mode not in DIRECTLY_USABLE_MODES:
        image = image.convert("RGBA")
    width, height = image.size

    shape = _shape_from_alpha(image)
    if shape is None:
        shape = _shape_from_luminance(image)
    if invert:
        shape = ImageOps.invert(shape)

    enlarged, scale = _enlarge(shape, min_size)
    return Mask(pixels=np.asarray(enlarged, dtype=np.uint8), width=width, height=height, scale=scale)


def _shape_from_alpha(image: Image.Image) -> Image.Image | None:
    """Read the artwork off the alpha channel, unless the image is barely transparent."""
    if "A" not in image.getbands():
        return None
    alpha = image.getchannel("A")
    transparent = np.asarray(alpha) < OPAQUE_CUTOFF
    if transparent.mean() < MIN_TRANSPARENT_FRACTION:
        return None
    return ImageOps.invert(alpha)


def _shape_from_luminance(image: Image.Image) -> Image.Image:
    """Read the artwork off the brightness, flipping it when the background is dark."""
    grey = _flatten_onto_white(image).convert("L")
    if _background_is_dark(grey):
        return ImageOps.invert(grey)
    return grey


def _flatten_onto_white(image: Image.Image) -> Image.Image:
    if "A" not in image.getbands():
        return image
    white = Image.new("RGBA", image.size, (255, 255, 255, 255))
    return Image.alpha_composite(white, image.convert("RGBA"))


def _background_is_dark(grey: Image.Image) -> bool:
    """Judge the background by the four corners, where a logo is least likely to reach."""
    pixels = np.asarray(grey, dtype=np.uint8)
    across = max(SMALLEST_CORNER, round(grey.width * CORNER_FRACTION))
    down = max(SMALLEST_CORNER, round(grey.height * CORNER_FRACTION))
    corners = np.concatenate(
        [
            pixels[:down, :across].ravel(),
            pixels[:down, -across:].ravel(),
            pixels[-down:, :across].ravel(),
            pixels[-down:, -across:].ravel(),
        ]
    )
    return float(np.median(corners)) < MID_GREY


def _enlarge(shape: Image.Image, min_size: int) -> tuple[Image.Image, float]:
    """Grow a small logo so potrace has smooth edges to follow."""
    longest = max(shape.size)
    if min_size <= longest:
        return shape, 1.0
    scale = min_size / longest
    enlarged = shape.resize((round(shape.width * scale), round(shape.height * scale)), Image.LANCZOS)
    return enlarged, scale
