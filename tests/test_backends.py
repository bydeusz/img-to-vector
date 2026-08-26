import re
import unittest

from img2vec.backends import render_eps, render_pdf, render_svg
from img2vec.trace import Contour, CurveTo, Drawing, LineTo, Point

LOGO_SIZE = 10


def _drawing(*contours, width=LOGO_SIZE, height=LOGO_SIZE):
    return Drawing(contours=tuple(contours), width=width, height=height)


def _band_along_the_top():
    """A contour hugging the top edge, so a flipped y axis is unmistakable."""
    return Contour(
        start=Point(0, 0),
        segments=(LineTo(Point(10, 0)), LineTo(Point(10, 2)), LineTo(Point(0, 2))),
    )


def _single_curve():
    return Contour(start=Point(0, 0), segments=(CurveTo(Point(1, 2), Point(3, 4), Point(5, 6)),))


class SvgTestCase(unittest.TestCase):
    def setUp(self):
        self.svg = render_svg(_drawing(_band_along_the_top()))

    def test_it_reports_the_logo_size(self):
        self.assertIn('width="10"', self.svg)
        self.assertIn('height="10"', self.svg)
        self.assertIn('viewBox="0 0 10 10"', self.svg)

    def test_it_paints_no_background(self):
        self.assertNotIn("<rect", self.svg)
        self.assertNotIn("#ffffff", self.svg.lower())

    def test_it_fills_black_with_the_even_odd_rule(self):
        self.assertIn('fill="#000000"', self.svg)
        self.assertIn('fill-rule="evenodd"', self.svg)

    def test_it_closes_every_contour(self):
        path = re.search(r'd="([^"]+)"', self.svg).group(1)

        self.assertEqual(path.count("M"), 1)
        self.assertTrue(path.rstrip().endswith("Z"))

    def test_it_keeps_the_traced_orientation(self):
        self.assertIn("M 0 0", self.svg)

    def test_it_writes_a_cubic_curve(self):
        self.assertIn("C 1 2 3 4 5 6", render_svg(_drawing(_single_curve())))

    def test_an_empty_drawing_still_renders(self):
        empty = render_svg(_drawing())

        self.assertIn("<svg", empty)
        self.assertIn("</svg>", empty)


class EpsTestCase(unittest.TestCase):
    def setUp(self):
        self.eps = render_eps(_drawing(_band_along_the_top()))

    def test_its_bounding_box_matches_the_logo(self):
        self.assertIn("%%BoundingBox: 0 0 10 10", self.eps)

    def test_it_flips_the_y_axis(self):
        self.assertIn("0 10 moveto", self.eps)
        self.assertIn("10 8 lineto", self.eps)

    def test_it_fills_black_with_the_even_odd_rule(self):
        self.assertIn("0 setgray", self.eps)
        self.assertEqual(self.eps.count("eofill"), 1)

    def test_it_paints_no_background(self):
        operators = {line.split()[-1] for line in self.eps.splitlines() if line and not line.startswith("%")}

        self.assertNotIn("1 setgray", self.eps)
        self.assertNotIn("fill", operators)
        self.assertNotIn("rectfill", operators)

    def test_it_writes_a_cubic_curve(self):
        self.assertIn("1 8 3 6 5 4 curveto", render_eps(_drawing(_single_curve())))


class PdfTestCase(unittest.TestCase):
    def setUp(self):
        self.pdf = render_pdf(_drawing(_band_along_the_top()))

    def test_it_declares_a_single_page_of_the_logo_size(self):
        self.assertTrue(self.pdf.startswith(b"%PDF-"))
        self.assertIn(b"/MediaBox [0 0 10 10]", self.pdf)
        self.assertIn(b"/Count 1", self.pdf)

    def test_it_flips_the_y_axis(self):
        self.assertIn(b"0 10 m", self.pdf)
        self.assertIn(b"10 8 l", self.pdf)

    def test_it_fills_black_with_the_even_odd_rule(self):
        self.assertIn(b"0 g", self.pdf)
        self.assertIn(b"f*", self.pdf)

    def test_it_marks_the_page_as_a_transparency_group(self):
        self.assertIn(b"/S /Transparency", self.pdf)

    def test_it_writes_a_cubic_curve(self):
        self.assertIn(b"1 8 3 6 5 4 c", render_pdf(_drawing(_single_curve())))

    def test_its_cross_reference_table_points_at_every_object(self):
        start = int(re.search(rb"startxref\s+(\d+)", self.pdf).group(1))

        self.assertTrue(self.pdf[start:].startswith(b"xref"))
        offsets = [int(match) for match in re.findall(rb"^(\d{10}) 00000 n", self.pdf[start:], re.M)]
        self.assertEqual(len(offsets), 4)
        for number, offset in enumerate(offsets, start=1):
            self.assertTrue(self.pdf[offset:].startswith(b"%d 0 obj" % number))


if __name__ == "__main__":
    unittest.main()
