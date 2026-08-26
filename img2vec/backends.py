"""Write traced contours as SVG, EPS and PDF, all black on nothing at all."""

from math import ceil

from img2vec.trace import Contour, Drawing, LineTo

CREATOR = "img2vec"
SVG_FILL = "#000000"
DECIMALS = 3


def render_svg(drawing: Drawing) -> str:
    """An SVG holding one black path and no background rectangle."""
    width = _number(drawing.width)
    height = _number(drawing.height)
    path = ""
    if drawing.contours:
        commands = " ".join(_svg_commands(contour) for contour in drawing.contours)
        path = f'<path fill="{SVG_FILL}" fill-rule="evenodd" d="{commands}"/>\n'
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
        f"{path}</svg>\n"
    )


def render_eps(drawing: Drawing) -> str:
    """An encapsulated PostScript page that paints nothing but the artwork."""
    lines = [
        "%!PS-Adobe-3.0 EPSF-3.0",
        f"%%Creator: {CREATOR}",
        f"%%BoundingBox: 0 0 {ceil(drawing.width)} {ceil(drawing.height)}",
        f"%%HiResBoundingBox: 0 0 {_number(drawing.width)} {_number(drawing.height)}",
        "%%Pages: 1",
        "%%EndComments",
        "%%Page: 1 1",
        "0 setgray",
        "newpath",
    ]
    for contour in drawing.contours:
        lines.extend(_eps_commands(contour, drawing.height))
    lines.extend(["eofill", "showpage", "%%EOF"])
    return "\n".join(lines) + "\n"


def render_pdf(drawing: Drawing) -> bytes:
    """A one page PDF whose page group is transparent, so only the artwork shows."""
    content = _pdf_content(drawing).encode("ascii")
    size = f"{_number(drawing.width)} {_number(drawing.height)}".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 "
        + size
        + b"] /Contents 4 0 R /Resources << >>"
        + b" /Group << /Type /Group /S /Transparency /CS /DeviceRGB >> >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"endstream",
    ]

    document = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(document))
        document += b"%d 0 obj\n" % number + body + b"\nendobj\n"

    table_at = len(document)
    document += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        document += b"%010d 00000 n \n" % offset
    document += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        table_at,
    )
    return bytes(document)


def _svg_commands(contour: Contour) -> str:
    commands = [f"M {_number(contour.start.x)} {_number(contour.start.y)}"]
    for segment in contour.segments:
        if isinstance(segment, LineTo):
            commands.append(f"L {_number(segment.end.x)} {_number(segment.end.y)}")
        else:
            commands.append(
                f"C {_number(segment.control_one.x)} {_number(segment.control_one.y)}"
                f" {_number(segment.control_two.x)} {_number(segment.control_two.y)}"
                f" {_number(segment.end.x)} {_number(segment.end.y)}"
            )
    commands.append("Z")
    return " ".join(commands)


def _eps_commands(contour: Contour, height: float) -> list[str]:
    return _flipped_commands(contour, height, move="moveto", line="lineto", curve="curveto", close="closepath")


def _pdf_content(drawing: Drawing) -> str:
    lines = ["0 g"]
    for contour in drawing.contours:
        lines.extend(_flipped_commands(contour, drawing.height, move="m", line="l", curve="c", close="h"))
    lines.append("f*")
    return "\n".join(lines) + "\n"


def _flipped_commands(contour: Contour, height: float, *, move: str, line: str, curve: str, close: str) -> list[str]:
    """The same path, with the y axis counted from the bottom as PostScript and PDF do."""

    def place(point):
        return f"{_number(point.x)} {_number(height - point.y)}"

    commands = [f"{place(contour.start)} {move}"]
    for segment in contour.segments:
        if isinstance(segment, LineTo):
            commands.append(f"{place(segment.end)} {line}")
        else:
            commands.append(
                f"{place(segment.control_one)} {place(segment.control_two)} {place(segment.end)} {curve}"
            )
    commands.append(close)
    return commands


def _number(value: float) -> str:
    text = f"{value:.{DECIMALS}f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text
