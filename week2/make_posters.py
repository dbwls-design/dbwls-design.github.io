"""Bitmap Echo - BAND BUSKING poster samples (week 2).

Every mark sits on one grid: the A3 sheet (297 x 420 mm) split into 3 mm cells,
99 x 140 cells. Each cell becomes a 36 x 36 px block -> 3564 x 5040 px PNG.

Run from the class folder (in the Claude app, keep uv's Python out of AppData):
    $env:UV_PYTHON_INSTALL_DIR = 'C:\\design-class\\.claude\\uv\\python'
    $env:UV_CACHE_DIR = 'C:\\design-class\\.claude\\uv\\cache'
    uv run --with pillow week2/make_posters.py          # draw the samples
    uv run --with pillow week2/make_posters.py probe    # print the pixel letters
"""
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FONT = HERE.parent / ".claude" / "skills" / "canvas-design" / "canvas-fonts" / "Silkscreen-Regular.ttf"
FONT_PX = 8  # Silkscreen is drawn on an 8 px em; at this size one font pixel = one cell

COLS, ROWS = 99, 140  # 297 x 420 mm in 3 mm cells
CELL = 36             # px per cell -> 3564 x 5040 px (A3 at 304.8 dpi)
MARGIN = 9            # 27 mm of white on every side
CLEAR = 2             # empty cells kept around every word

WHITE = (250, 250, 246)
BLACK = (17, 17, 17)
MAGENTA = (196, 0, 122)  # deep ink magenta, never fluorescent

DATE = "2026.11.04"
BOTTOM = ROWS - MARGIN - 1  # last row inside the margin
RIGHT = COLS - MARGIN - 1   # last column inside the margin


def letter_cells(text):
    """Return the lit pixels of `text` as a set of (x, y), plus width and height."""
    font = ImageFont.truetype(str(FONT), FONT_PX)
    left, top, right, bottom = font.getbbox(text)
    img = Image.new("1", (right - left + 4, bottom - top + 4), 0)
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"  # no anti-aliasing: every pixel is fully on or off
    draw.text((-left + 2, -top + 2), text, font=font, fill=1)
    px = img.load()
    lit = {(x, y) for y in range(img.height) for x in range(img.width) if px[x, y]}
    min_x = min(x for x, _ in lit)
    min_y = min(y for _, y in lit)
    lit = {(x - min_x, y - min_y) for x, y in lit}
    width = max(x for x, _ in lit) + 1
    height = max(y for _, y in lit) + 1
    return lit, width, height


def text_size(text, scale):
    _, w, h = letter_cells(text)
    return w * scale, h * scale


def ring(cx, cy, r):
    """Cells of a one-cell-thick circle (midpoint algorithm), in order around it."""
    cells = set()
    x, y, d = r, 0, 1 - r
    while x >= y:
        for px, py in ((x, y), (y, x), (-y, x), (-x, y), (-x, -y), (-y, -x), (y, -x), (x, -y)):
            cells.add((cx + px, cy + py))
        y += 1
        if d < 0:
            d += 2 * y + 1
        else:
            x -= 1
            d += 2 * (y - x) + 1
    return sorted(cells, key=lambda c: math.atan2(c[1] - cy, c[0] - cx))


class Sheet:
    """One poster: a 99 x 140 grid where every cell is white, black or magenta."""

    def __init__(self):
        self.cells = {}     # (x, y) -> color
        self.owner = {}     # (x, y) -> name of the element that drew it
        self.words = set()  # text elements, kept clear of everything else

    def put(self, x, y, color, owner):
        if not (MARGIN <= x <= RIGHT and MARGIN <= y <= BOTTOM):
            raise ValueError(f"{owner} crosses the margin at {(x, y)}")
        other = self.owner.get((x, y))
        if other not in (None, owner):
            raise ValueError(f"{owner} overlaps {other} at {(x, y)}")
        self.cells[(x, y)] = color
        self.owner[(x, y)] = owner

    def block(self, x, y, w, h, color, owner):
        for dy in range(h):
            for dx in range(w):
                self.put(x + dx, y + dy, color, owner)

    def disc(self, cx, cy, r, color, owner):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * (r + 1):
                    self.put(x, y, color, owner)

    def text(self, text, x, y, scale, owner):
        lit, w, h = letter_cells(text)
        for px, py in lit:
            self.block(x + px * scale, y + py * scale, scale, scale, BLACK, owner)
        self.words.add(owner)
        return w * scale, h * scale

    def headline(self, x, y, scale=2, gap=4):
        """BAND over BUSKING, left-aligned."""
        _, h = self.text("BAND", x, y, scale, "band")
        self.text("BUSKING", x, y + h + gap, scale, "busking")

    def check_clearance(self):
        for (x, y), owner in self.owner.items():
            if owner not in self.words:
                continue
            for dy in range(-CLEAR, CLEAR + 1):
                for dx in range(-CLEAR, CLEAR + 1):
                    other = self.owner.get((x + dx, y + dy))
                    if other not in (None, owner):
                        raise ValueError(f"{owner} is crowded by {other} near {(x, y)}")

    def save(self, path):
        self.check_clearance()
        img = Image.new("RGB", (COLS * CELL, ROWS * CELL), WHITE)
        draw = ImageDraw.Draw(img)
        for (x, y), color in self.cells.items():
            draw.rectangle([x * CELL, y * CELL, (x + 1) * CELL - 1, (y + 1) * CELL - 1], fill=color)
        img.save(path, dpi=(304.8, 304.8))
        magenta = sum(1 for c in self.cells.values() if c == MAGENTA)
        ink = len(self.cells)
        print(f"{path.name}: {img.width} x {img.height} px, "
              f"ink {ink / (COLS * ROWS):.1%} of the sheet, magenta {magenta} cells")


def circle():
    """Top view of a busking circle: the band as a magenta source, sound rings, the crowd's arc."""
    s = Sheet()
    s.headline(MARGIN, MARGIN)
    s.text(DATE, MARGIN, BOTTOM - 4, 1, "date")
    cx, cy = COLS // 2, 88
    s.disc(cx, cy, 3, MAGENTA, "source")
    for r, step in ((8, 2), (14, 3), (21, 4)):  # each echo sparser than the last
        for i, (x, y) in enumerate(ring(cx, cy, r)):
            if i % step == 0:
                s.put(x, y, BLACK, f"ring{r}")
    jitter = (0, 1, 0, -1, 1, 0, -1, 1, 0, 1, 0)
    for r, count, start, end in ((28, 11, 200, 340), (33, 10, 207, 333)):
        for i in range(count):
            a = math.radians(start + (end - start) * i / (count - 1))
            x = round(cx + (r + jitter[i]) * math.cos(a) - 0.5)
            y = round(cy + (r + jitter[i]) * math.sin(a) - 0.5)
            s.block(x, y, 2, 2, BLACK, "crowd")
    return s


def meter():
    """The date's digits as a segmented level meter; the loudest bar keeps a magenta peak."""
    s = Sheet()
    digits = [int(c) for c in DATE if c.isdigit()]  # 2 0 2 6 1 1 0 4
    floor = 96
    for i, d in enumerate(digits):
        x = MARGIN + i * 10
        segments = 2 * d + 1
        for j in range(segments):
            s.block(x, floor - 3 * j - 1, 6, 2, BLACK, "meter")
        if d == max(digits):
            s.block(x, floor - 3 * (segments + 1) - 1, 6, 2, MAGENTA, "peak")
    busking_w, _ = text_size("BUSKING", 2)
    s.block(MARGIN, floor + 4, busking_w, 1, BLACK, "street")
    s.headline(MARGIN, BOTTOM - 23)
    date_w, _ = text_size(DATE, 1)
    s.text(DATE, MARGIN + busking_w - date_w, MARGIN, 1, "date")
    return s


def wave():
    """One stair-stepped sound wave: silence, crescendo, silence. The loudest crest is magenta."""
    s = Sheet()
    s.text("BAND BUSKING", MARGIN, MARGIN, 1, "headline")
    date_w, date_h = text_size(DATE, 1)
    s.text(DATE, RIGHT - date_w + 1, BOTTOM - date_h + 1, 1, "date")
    cy, amp, cycles = 70, 18, 6.5  # 6.5 cycles puts a crest exactly at the centre
    prev = None
    for x in range(MARGIN, RIGHT + 1):
        t = (x - MARGIN) / (RIGHT - MARGIN)
        y = round(cy - amp * math.sin(math.pi * t) ** 2 * math.sin(2 * math.pi * cycles * t))
        color = MAGENTA if abs(t - 0.5) < 0.25 / cycles else BLACK
        lo, hi = (y, y) if prev is None else (min(prev, y), max(prev, y))
        for yy in range(lo, hi + 1):
            s.put(x, yy, color, "wave")
        prev = y
    ruler = cy + amp + 6
    for x in range(MARGIN, RIGHT + 1, 3):
        s.block(x, ruler, 1, 3 if (x - MARGIN) % 15 == 0 else 1, BLACK, "ruler")
    return s


def lift():
    """BAND BUSKING set large; pixels lift off the letters like sound into the air."""
    s = Sheet()
    s.text(DATE, MARGIN, MARGIN, 1, "date")
    _, busking_h = text_size("BUSKING", 2)
    _, band_h = text_size("BAND", 3)
    busking_top = BOTTOM - busking_h + 1  # BUSKING sits on the bottom margin
    band_top = busking_top - 4 - band_h   # BAND, three times larger, 4 rows above it
    s.text("BAND", MARGIN, band_top, 3, "band")
    s.text("BUSKING", MARGIN, busking_top, 2, "busking")
    lit, band_w, _ = letter_cells("BAND")
    roof = {x for x, y in lit if y == 0}  # columns where BAND's letters have a top edge
    rng = random.Random(20261104)
    lowest = band_top - CLEAR - 1
    for y in range(MARGIN + 9, lowest + 1):
        p = 0.10 * math.exp(-(lowest - y) / 15)
        for x in range(MARGIN, MARGIN + band_w * 3):
            weight = 1.0 if (x - MARGIN) // 3 in roof else 0.35
            if rng.random() < p * weight:
                s.put(x, y, MAGENTA if rng.random() < 0.15 else BLACK, "lift")
    return s


def probe():
    for text in ["BAND", "BUSKING", "BAND BUSKING", "2026", "11.04", DATE]:
        lit, w, h = letter_cells(text)
        print(f"{text!r}: {w} x {h} pixels")
        for y in range(h):
            print("   " + "".join("#" if (x, y) in lit else "." for x in range(w)))


if __name__ == "__main__":
    if sys.argv[1:] == ["probe"]:
        probe()
    else:
        for n, make in enumerate((circle, meter, wave, lift), start=1):
            make().save(HERE / f"bitmap-echo_{n}_{make.__name__}.png")
