"""Convert every image in a folder to vector files, one progress line at a time."""

import argparse
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from PIL import UnidentifiedImageError

from img2vec.backends import render_eps, render_pdf, render_svg
from img2vec.preprocess import DEFAULT_MIN_SIZE, build_mask, load_image
from img2vec.trace import DEFAULT_ALPHAMAX, DEFAULT_THRESHOLD, DEFAULT_TURDSIZE, trace_mask

IMAGE_SUFFIXES = (".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp")
RENDERERS = {"svg": render_svg, "pdf": render_pdf, "eps": render_eps}
ALL_FORMATS = tuple(RENDERERS)
DEFAULT_INPUT = Path("input")
DEFAULT_OUTPUT = Path("output")
NAME_WIDTH = 26
KILOBYTE = 1024


@dataclass(frozen=True)
class Settings:
    """Everything the user can turn, gathered in one place."""

    invert: bool = False
    min_size: int = DEFAULT_MIN_SIZE
    threshold: float = DEFAULT_THRESHOLD
    turdsize: int = DEFAULT_TURDSIZE
    alphamax: float = DEFAULT_ALPHAMAX


@dataclass(frozen=True)
class Conversion:
    source: Path
    contours: int
    written_bytes: int
    formats: tuple[str, ...] = field(default_factory=tuple)


def find_images(directory: Path) -> list[Path]:
    """Every image sitting directly in the folder, in a stable order."""
    if not directory.is_dir():
        return []
    found = [path for path in directory.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES]
    return sorted(found, key=lambda path: path.name.lower())


def convert_file(source: Path, destination: Path, formats: tuple[str, ...], settings: Settings) -> Conversion:
    """Trace one image and write it out in each requested format."""
    mask = build_mask(load_image(source), invert=settings.invert, min_size=settings.min_size)
    drawing = trace_mask(
        mask,
        threshold=settings.threshold,
        turdsize=settings.turdsize,
        alphamax=settings.alphamax,
    )
    written_bytes = 0
    for name in formats:
        target = destination / f"{source.stem}.{name}"
        written_bytes += _write(RENDERERS[name](drawing), target)
    return Conversion(source=source, contours=len(drawing.contours), written_bytes=written_bytes, formats=formats)


def main(argv: list[str] | None = None, stream=None) -> int:
    options = _parse_arguments(argv)
    report = stream if stream is not None else sys.stdout
    sources = find_images(options.input)
    if not sources:
        print(f"geen afbeeldingen gevonden in {options.input}/", file=report)
        return 0

    options.output.mkdir(parents=True, exist_ok=True)
    settings = Settings(
        invert=options.invert,
        min_size=options.min_size,
        threshold=options.threshold,
        turdsize=options.turdsize,
        alphamax=options.alphamax,
    )

    started = time.perf_counter()
    failures = 0
    for index, source in enumerate(sources, start=1):
        prefix = _prefix(index, len(sources), source.name)
        _announce(prefix, report)
        try:
            conversion = convert_file(source, options.output, options.formats, settings)
        except Exception as problem:
            failures += 1
            _replace(f"{prefix}mislukt: {_reason(problem)}", report)
        else:
            _replace(f"{prefix}{_result(conversion)}", report)

    _summarise(len(sources), failures, time.perf_counter() - started, report)
    return 1 if failures else 0


def _parse_arguments(argv):
    parser = argparse.ArgumentParser(
        prog="img2vec",
        description="Zet de logo's in input/ om naar zwarte vectoren met een transparante achtergrond.",
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="map met afbeeldingen")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="map voor de vectoren")
    parser.add_argument("--formats", type=_formats, default=ALL_FORMATS, help="svg, pdf, eps of een komma-lijst")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD, help="grens tussen vorm en achtergrond")
    parser.add_argument("--invert", action="store_true", help="draai vorm en achtergrond om")
    parser.add_argument("--turdsize", type=int, default=DEFAULT_TURDSIZE, help="onderdruk vlekjes tot deze grootte")
    parser.add_argument("--alphamax", type=float, default=DEFAULT_ALPHAMAX, help="lager is hoekiger, hoger is ronder")
    parser.add_argument("--min-size", type=int, default=DEFAULT_MIN_SIZE, help="vergroot kleine logo's eerst tot deze grootte (0 = laat staan)")
    return parser.parse_args(argv)


def _formats(value):
    chosen = tuple(name.strip().lower() for name in value.split(",") if name.strip())
    unknown = [name for name in chosen if name not in RENDERERS]
    if unknown or not chosen:
        raise argparse.ArgumentTypeError(f"kies uit {', '.join(ALL_FORMATS)}")
    return chosen


def _write(rendered, target: Path) -> int:
    if isinstance(rendered, bytes):
        target.write_bytes(rendered)
    else:
        target.write_text(rendered, encoding="utf-8")
    return target.stat().st_size


def _prefix(index: int, total: int, name: str) -> str:
    counter = f"[{index:>{len(str(total))}}/{total}]"
    return f"{counter} {_fit(name)}  "


def _fit(name: str) -> str:
    if len(name) > NAME_WIDTH:
        return name[: NAME_WIDTH - 1] + "…"
    return name.ljust(NAME_WIDTH)


def _result(conversion: Conversion) -> str:
    kilobytes = conversion.written_bytes / KILOBYTE
    return f"ok    {conversion.contours} paden, {kilobytes:.1f} KB  {' '.join(conversion.formats)}"


def _reason(problem: Exception) -> str:
    if isinstance(problem, UnidentifiedImageError):
        return "geen leesbare afbeelding"
    return str(problem) or problem.__class__.__name__


def _announce(prefix: str, report) -> None:
    if _is_live(report):
        report.write(f"{prefix}bezig...")
        report.flush()


def _replace(line: str, report) -> None:
    if _is_live(report):
        report.write("\r\033[K")
    report.write(line + "\n")
    report.flush()


def _summarise(total: int, failures: int, seconds: float, report) -> None:
    done = total - failures
    tail = f" {failures} mislukt (zie hierboven)." if failures else ""
    print(f"\n{done} van {total} geslaagd in {seconds:.1f}s.{tail}", file=report)


def _is_live(report) -> bool:
    return hasattr(report, "isatty") and report.isatty()
