import unittest

import numpy as np

from img2vec.preprocess import Mask
from img2vec.trace import CurveTo, LineTo, trace_mask

WHITE = 255
BLACK = 0


def _mask_of(pixels, *, scale=1.0):
    """Wrap a raw array as a mask, with the original size implied by the scale."""
    height, width = pixels.shape
    return Mask(pixels=pixels, width=round(width / scale), height=round(height / scale), scale=scale)


def _square(size=40, box=slice(10, 30)):
    pixels = np.full((size, size), WHITE, dtype=np.uint8)
    pixels[box, box] = BLACK
    return pixels


def _all_points(drawing):
    points = []
    for contour in drawing.contours:
        points.append(contour.start)
        for segment in contour.segments:
            points.append(segment.end)
    return points


class TraceMaskTestCase(unittest.TestCase):
    """Dark areas become closed contours, holes included."""

    def test_a_solid_square_becomes_one_contour(self):
        drawing = trace_mask(_mask_of(_square()))

        self.assertEqual(len(drawing.contours), 1)

    def test_a_hole_becomes_a_contour_of_its_own(self):
        pixels = _square()
        pixels[15:25, 15:25] = WHITE

        drawing = trace_mask(_mask_of(pixels))

        self.assertEqual(len(drawing.contours), 2)

    def test_straight_edges_become_line_segments(self):
        drawing = trace_mask(_mask_of(_square()))

        self.assertTrue(all(isinstance(segment, LineTo) for segment in drawing.contours[0].segments))

    def test_round_edges_become_curve_segments(self):
        grid = np.ogrid[:60, :60]
        circle = (grid[0] - 30) ** 2 + (grid[1] - 30) ** 2 < 400
        pixels = np.where(circle, BLACK, WHITE).astype(np.uint8)

        drawing = trace_mask(_mask_of(pixels))

        self.assertTrue(any(isinstance(segment, CurveTo) for segment in drawing.contours[0].segments))


class TraceOptionsTestCase(unittest.TestCase):
    """The potrace knobs reach the tracer."""

    def setUp(self):
        self.speckled = _square()
        self.speckled[35, 35] = BLACK

    def test_a_speckle_is_dropped_at_the_default_turd_size(self):
        drawing = trace_mask(_mask_of(self.speckled))

        self.assertEqual(len(drawing.contours), 1)

    def test_a_speckle_survives_when_despeckling_is_off(self):
        drawing = trace_mask(_mask_of(self.speckled), turdsize=0)

        self.assertEqual(len(drawing.contours), 2)

    def test_the_threshold_decides_what_counts_as_dark(self):
        pixels = np.full((40, 40), WHITE, dtype=np.uint8)
        pixels[10:30, 10:30] = 160

        self.assertEqual(len(trace_mask(_mask_of(pixels), threshold=0.5).contours), 0)
        self.assertEqual(len(trace_mask(_mask_of(pixels), threshold=0.7).contours), 1)


class TraceScalingTestCase(unittest.TestCase):
    """An enlarged mask still describes a logo at its original size."""

    def setUp(self):
        pixels = np.full((200, 200), WHITE, dtype=np.uint8)
        pixels[50:150, 50:150] = BLACK
        self.drawing = trace_mask(_mask_of(pixels, scale=10.0))

    def test_the_drawing_reports_the_original_size(self):
        self.assertEqual((self.drawing.width, self.drawing.height), (20, 20))

    def test_coordinates_are_divided_by_the_scale(self):
        points = _all_points(self.drawing)

        self.assertTrue(all(0 <= point.x <= 20 and 0 <= point.y <= 20 for point in points))
        self.assertAlmostEqual(min(point.x for point in points), 5.0, places=1)
        self.assertAlmostEqual(max(point.x for point in points), 15.0, places=1)


if __name__ == "__main__":
    unittest.main()
