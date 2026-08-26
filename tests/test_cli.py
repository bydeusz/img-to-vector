import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from img2vec.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent


def _write_logo(path, size=(40, 40)):
    """A png standing in for a logo: a black block on a white field."""
    image = Image.new("RGB", size, "white")
    image.paste("black", (10, 10, 30, 30))
    image.save(path)


class CliTestCase(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.input = Path(self.directory.name) / "input"
        self.output = Path(self.directory.name) / "output"
        self.input.mkdir()
        self.report = io.StringIO()

    def run_tool(self, *extra):
        arguments = ["--input", str(self.input), "--output", str(self.output), "--min-size", "0", *extra]
        return main(arguments, stream=self.report)

    def test_every_image_becomes_three_files(self):
        _write_logo(self.input / "first.png")
        _write_logo(self.input / "second.png")

        self.run_tool()

        for stem in ("first", "second"):
            for suffix in ("svg", "pdf", "eps"):
                self.assertTrue((self.output / f"{stem}.{suffix}").exists(), f"{stem}.{suffix} ontbreekt")

    def test_only_the_requested_formats_are_written(self):
        _write_logo(self.input / "logo.png")

        self.run_tool("--formats", "svg")

        self.assertTrue((self.output / "logo.svg").exists())
        self.assertFalse((self.output / "logo.pdf").exists())

    def test_it_reports_a_line_for_every_image(self):
        _write_logo(self.input / "first.png")
        _write_logo(self.input / "second.png")

        self.run_tool()

        printed = self.report.getvalue()
        self.assertIn("[1/2]", printed)
        self.assertIn("[2/2]", printed)
        self.assertIn("first.png", printed)
        self.assertIn("second.png", printed)

    def test_it_ends_with_a_summary(self):
        _write_logo(self.input / "logo.png")

        self.run_tool()

        self.assertIn("1 van 1 geslaagd", self.report.getvalue())

    def test_files_that_are_not_images_are_skipped(self):
        _write_logo(self.input / "logo.png")
        (self.input / "notes.txt").write_text("geen afbeelding")

        self.run_tool()

        self.assertNotIn("notes.txt", self.report.getvalue())

    def test_it_succeeds_quietly_when_everything_converts(self):
        _write_logo(self.input / "logo.png")

        self.assertEqual(self.run_tool(), 0)


class CliFailureTestCase(CliTestCase):
    def test_a_broken_file_does_not_stop_the_others(self):
        (self.input / "broken.png").write_bytes(b"dit is geen png")
        _write_logo(self.input / "good.png")

        self.run_tool()

        self.assertTrue((self.output / "good.svg").exists())
        self.assertIn("mislukt", self.report.getvalue())

    def test_a_broken_file_makes_the_run_fail(self):
        (self.input / "broken.png").write_bytes(b"dit is geen png")

        self.assertEqual(self.run_tool(), 1)

    def test_an_empty_input_folder_is_not_an_error(self):
        self.assertEqual(self.run_tool(), 0)
        self.assertIn("geen afbeeldingen", self.report.getvalue())


class ModuleEntryPointTestCase(unittest.TestCase):
    """`python -m img2vec` is what the Pipfile script and run.sh call."""

    def test_it_converts_the_input_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input"
            destination = Path(directory) / "output"
            source.mkdir()
            _write_logo(source / "logo.png")

            finished = subprocess.run(
                [sys.executable, "-m", "img2vec", "--input", str(source), "--output", str(destination), "--min-size", "0"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(finished.returncode, 0, finished.stderr)
            self.assertTrue((destination / "logo.svg").exists())


if __name__ == "__main__":
    unittest.main()
