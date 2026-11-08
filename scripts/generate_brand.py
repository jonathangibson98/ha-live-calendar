#!/usr/bin/env python3
"""Generate the Live Calendar logos (SVG + PNG) from one set of parameters.

Usage:  python3 scripts/generate_brand.py
Needs:  Pillow (pip install pillow). Uses Inter or DejaVu Sans if installed.
Output: images/*.svg and custom_components/live_calendar/brand/*.png
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "custom_components" / "live_calendar" / "brand"
IMAGES = ROOT / "images"

TOP, BOTTOM = (0, 179, 164), (30, 111, 217)  # teal -> blue
INK = (27, 42, 65)
YELLOW = (255, 209, 102)
HEADER = (207, 227, 255)
CELL = (160, 190, 235)

FONTS = [
    "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

# Arc geometry in a 256 x 256 design space (centre of the "live" signal).
CX, CY = 178, 82
ARCS = [(24, 10), (42, 10)]  # (radius, stroke width)
ARC_FROM, ARC_TO = -85, -5  # degrees, 0 = right, negative = up


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONTS:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render_icon(size: int) -> Image.Image:
    """Square app icon with transparent corners."""
    s = 4  # supersampling
    px = size * s
    k = px / 256

    grad = Image.linear_gradient("L").resize((px, px))
    base = Image.composite(
        Image.new("RGB", (px, px), BOTTOM), Image.new("RGB", (px, px), TOP), grad
    )
    mask = Image.new("L", (px, px), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, px - 1, px - 1), radius=56 * k, fill=255)
    img = base.convert("RGBA")
    img.putalpha(mask)

    d = ImageDraw.Draw(img)

    def box(x0, y0, x1, y1):
        return (x0 * k, y0 * k, x1 * k, y1 * k)

    # calendar body + header band
    d.rounded_rectangle(box(48, 80, 176, 196), radius=16 * k, fill=(255, 255, 255))
    d.rounded_rectangle(box(48, 80, 176, 114), radius=16 * k, fill=HEADER)
    d.rectangle(box(48, 100, 176, 114), fill=HEADER)
    # binder rings
    for x in (82, 142):
        d.rounded_rectangle(box(x, 66, x + 12, 92), radius=6 * k, fill=(255, 255, 255))
    # day grid
    for row, y in enumerate((128, 156)):
        for col, x in enumerate((64, 94, 124, 150)):
            if row == 1 and col == 3:
                continue
            fill = BOTTOM if (row == 1 and col == 2) else CELL  # col 2, row 1 = "today"
            d.rounded_rectangle(box(x, y, x + 18, y + 18), radius=5 * k, fill=fill)

    # live signal arcs + dot
    for r, w in ARCS:
        ro = r + w / 2  # PIL draws the stroke inward from the bbox edge
        d.arc(
            box(CX - ro, CY - ro, CX + ro, CY + ro),
            ARC_FROM,
            ARC_TO,
            fill=(255, 255, 255),
            width=int(w * k),
        )
        for ang in (ARC_FROM, ARC_TO):  # round caps
            ex = CX + r * math.cos(math.radians(ang))
            ey = CY + r * math.sin(math.radians(ang))
            d.ellipse(box(ex - w / 2, ey - w / 2, ex + w / 2, ey + w / 2), fill=(255, 255, 255))
    d.ellipse(box(CX - 9, CY - 9, CX + 9, CY + 9), fill=YELLOW)

    return img.resize((size, size), Image.LANCZOS)


def render_logo(height: int, dark: bool) -> Image.Image:
    """Landscape logo: icon + wordmark, transparent background, no padding."""
    s = height / 256
    text = "Live Calendar"
    font = _font(int(104 * s))
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    bbox = probe.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    gap = int(28 * s)
    width = height + gap + tw
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    img.alpha_composite(render_icon(height), (0, 0))
    color = (255, 255, 255) if dark else INK
    ImageDraw.Draw(img).text(
        (height + gap - bbox[0], (height - th) // 2 - bbox[1]),
        text,
        font=font,
        fill=color,
    )
    return img


def icon_svg() -> str:
    rings = "".join(
        f'<rect x="{x}" y="66" width="12" height="26" rx="6" fill="#fff"/>' for x in (82, 142)
    )
    cells = ""
    for row, y in enumerate((128, 156)):
        for col, x in enumerate((64, 94, 124, 150)):
            if row == 1 and col == 3:
                continue
            fill = "#1E6FD9" if (row == 1 and col == 2) else "#A0BEEB"
            cells += f'<rect x="{x}" y="{y}" width="18" height="18" rx="5" fill="{fill}"/>'
    arcs = ""
    for r, w in ARCS:
        x0 = CX + r * math.cos(math.radians(ARC_FROM))
        y0 = CY + r * math.sin(math.radians(ARC_FROM))
        x1 = CX + r * math.cos(math.radians(ARC_TO))
        y1 = CY + r * math.sin(math.radians(ARC_TO))
        arcs += (
            f'<path d="M{x0:.2f} {y0:.2f} A{r} {r} 0 0 1 {x1:.2f} {y1:.2f}" fill="none" '
            f'stroke="#fff" stroke-width="{w}" stroke-linecap="round"/>'
        )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#00B3A4"/><stop offset="1" stop-color="#1E6FD9"/>'
        "</linearGradient></defs>"
        '<rect width="256" height="256" rx="56" fill="url(#g)"/>'
        '<rect x="48" y="80" width="128" height="116" rx="16" fill="#fff"/>'
        '<path d="M48 96a16 16 0 0 1 16-16h96a16 16 0 0 1 16 16v18H48z" fill="#CFE3FF"/>'
        f"{rings}{cells}"
        f'{arcs}<circle cx="{CX}" cy="{CY}" r="9" fill="#FFD166"/>'
        "</svg>"
    )


def banner_svg() -> str:
    inner = icon_svg().replace('width="256" height="256"', 'x="48" y="32" width="256" height="256"', 1)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 320" width="1280" height="320">'
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#0F1B2D"/><stop offset="1" stop-color="#16345F"/>'
        "</linearGradient></defs>"
        '<rect width="1280" height="320" rx="24" fill="url(#bg)"/>'
        f"{inner}"
        '<g font-family="Inter, -apple-system, Segoe UI, Roboto, Arial, sans-serif">'
        '<text x="336" y="160" font-size="84" font-weight="800" fill="#FFFFFF">Live Calendar</text>'
        '<text x="338" y="218" font-size="32" fill="#9FC2F5">'
        "Near-instant calendar sync for Home Assistant</text></g></svg>"
    )


def main() -> None:
    BRAND.mkdir(parents=True, exist_ok=True)
    IMAGES.mkdir(parents=True, exist_ok=True)
    render_icon(256).save(BRAND / "icon.png", optimize=True)
    render_icon(512).save(BRAND / "icon@2x.png", optimize=True)
    for dark in (False, True):
        prefix = "dark_" if dark else ""
        render_logo(256, dark).save(BRAND / f"{prefix}logo.png", optimize=True)
        render_logo(512, dark).save(BRAND / f"{prefix}logo@2x.png", optimize=True)
    render_icon(512).save(IMAGES / "icon.png", optimize=True)
    (IMAGES / "icon.svg").write_text(icon_svg(), encoding="utf-8")
    (IMAGES / "banner.svg").write_text(banner_svg(), encoding="utf-8")
    print("Brand assets written to", BRAND, "and", IMAGES)


if __name__ == "__main__":
    main()
