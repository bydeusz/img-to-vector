import tempfile
import unittest
from pathlib import Path

from PIL import Image

from img2vec.preprocess import build_mask, load_image

SHAPE_CENTRE = (20, 20)
BACKGROUND_CORNER = (2, 2)


def _canvas(mode, background, size=(40, 40)):
    """A blank image to paste a fake logo onto."""
    return Image.new(mode, size, background)


def _logo_on(image, colour, box=(10, 10, 30, 30)):
    """Paste a solid rectangle standing in for the artwork of a logo."""
    image.paste(colour, box)
    return image


def _value_at(mask, position):
    x, y = position
    return int(mask.pixels[y, x])


class BuildMaskTestCase(unittest.TestCase):
    """The artwork of a logo always ends up dark, whatever the source looks like."""

    def assertShapeIsDark(self, mask):
        self.assertLess(_value_at(mask, SHAPE_CENTRE), 128)
        self.assertGreater(_value_at(mask, BACKGROUND_CORNER), 128)

    def test_black_artwork_on_white_stays_dark(self):
        image = _logo_on(_canvas("RGB", "white"), "black")

        self.assertShapeIsDark(build_mask(image, min_size=0))

    def test_white_artwork_on_transparency_becomes_dark(self):
        image = _logo_on(_canvas("RGBA", (0, 0, 0, 0)), (255, 255, 255, 255))

        self.assertShapeIsDark(build_mask(image, min_size=0))

    def test_black_artwork_on_transparency_becomes_dark(self):
        image = _logo_on(_canvas("RGBA", (0, 0, 0, 0)), (0, 0, 0, 255))

        self.assertShapeIsDark(build_mask(image, min_size=0))

    def test_light_artwork_on_a_dark_background_is_inverted(self):
        image = _logo_on(_canvas("RGB", "black"), "white")

        self.assertShapeIsDark(build_mask(image, min_size=0))

    def test_a_nearly_opaque_alpha_channel_is_ignored(self):
        image = _logo_on(_canvas("RGBA", (255, 255, 255, 255)), (0, 0, 0, 255))
        image.paste((0, 0, 0, 0), (0, 0, 4, 4))

        self.assertShapeIsDark(build_mask(image, min_size=0))

    def test_invert_overrides_the_detected_polarity(self):
        image = _logo_on(_canvas("RGB", "white"), "black")

        mask = build_mask(image, invert=True, min_size=0)

        self.assertGreater(_value_at(mask, SHAPE_CENTRE), 128)
        self.assertLess(_value_at(mask, BACKGROUND_CORNER), 128)


class MaskScalingTestCase(unittest.TestCase):
    """Small logos are enlarged before tracing, without losing their real size."""

    def setUp(self):
        self.image = _logo_on(_canvas("RGB", "white"), "black")

    def test_a_small_image_is_enlarged_up_to_the_minimum(self):
        mask = build_mask(self.image, min_size=400)

        self.assertEqual(mask.pixels.shape, (400, 400))
        self.assertEqual(mask.scale, 10)

    def test_the_original_size_is_kept_alongside_the_enlarged_pixels(self):
        mask = build_mask(self.image, min_size=400)

        self.assertEqual((mask.width, mask.height), (40, 40))

    def test_an_image_above_the_minimum_is_left_alone(self):
        mask = build_mask(self.image, min_size=20)

        self.assertEqual(mask.pixels.shape, (40, 40))
        self.assertEqual(mask.scale, 1)

    def test_enlarging_is_off_unless_it_is_asked_for(self):
        mask = build_mask(self.image)

        self.assertEqual(mask.pixels.shape, (40, 40))
        self.assertEqual(mask.scale, 1)


class LoadImageTestCase(unittest.TestCase):
    """Reading a file applies whatever rotation the camera recorded."""

    def test_an_exif_rotation_is_applied(self):
        exif = Image.Exif()
        exif[274] = 6
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sideways.jpg"
            Image.new("RGB", (60, 40), "white").save(path, exif=exif)

            self.assertEqual(load_image(path).size, (40, 60))


if __name__ == "__main__":
    unittest.main()
