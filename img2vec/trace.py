"""Trace a mask into closed contours, expressed at the logo's original size."""

from dataclasses import dataclass

from potrace import Bitmap

from img2vec.preprocess import Mask

DEFAULT_THRESHOLD = 0.5
DEFAULT_TURDSIZE = 2
DEFAULT_ALPHAMAX = 1.0
DEFAULT_OPTTOLERANCE = 0.2


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class LineTo:
    end: Point


@dataclass(frozen=True)
class CurveTo:
    control_one: Point
    control_two: Point
    end: Point


@dataclass(frozen=True)
class Contour:
    """One closed outline. Outlines and the holes inside them are both contours."""

    start: Point
    segments: tuple[LineTo | CurveTo, ...]


@dataclass(frozen=True)
class Drawing:
    contours: tuple[Contour, ...]
    width: float
    height: float


def trace_mask(
    mask: Mask,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    turdsize: int = DEFAULT_TURDSIZE,
    alphamax: float = DEFAULT_ALPHAMAX,
    opttolerance: float = DEFAULT_OPTTOLERANCE,
    opticurve: bool = True,
) -> Drawing:
    """Run potrace over the dark pixels of the mask."""
    path = Bitmap(mask.pixels, blacklevel=threshold).trace(
        turdsize=turdsize,
        alphamax=alphamax,
        opticurve=opticurve,
        opttolerance=opttolerance,
    )
    contours = tuple(_contour_of(curve, mask.scale) for curve in path.curves or ())
    return Drawing(contours=contours, width=mask.width, height=mask.height)


def _contour_of(curve, scale: float) -> Contour:
    segments: list[LineTo | CurveTo] = []
    for segment in curve.segments:
        if segment.is_corner:
            segments.append(LineTo(_shrink(segment.c, scale)))
            segments.append(LineTo(_shrink(segment.end_point, scale)))
        else:
            segments.append(
                CurveTo(
                    _shrink(segment.c1, scale),
                    _shrink(segment.c2, scale),
                    _shrink(segment.end_point, scale),
                )
            )
    return Contour(start=_shrink(curve.start_point, scale), segments=tuple(segments))


def _shrink(point, scale: float) -> Point:
    return Point(x=point.x / scale, y=point.y / scale)
