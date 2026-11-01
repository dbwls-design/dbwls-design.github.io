"""Painted Echo - BAND BUSKING poster samples, painted version (week 2).

Paper grain, dry-brush magenta strokes and wide black type.
A3 portrait, 3564 x 5040 px (304.8 dpi).

Run from the class folder (in the Claude app, keep uv's Python out of AppData):
    $env:UV_PYTHON_INSTALL_DIR = 'C:\\design-class\\.claude\\uv\\python'
    $env:UV_CACHE_DIR = 'C:\\design-class\\.claude\\uv\\cache'
    uv run --with pillow week2/make_paint_posters.py
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
FONTS = HERE.parent / ".claude" / "skills" / "canvas-design" / "canvas-fonts"
TITLE_FONT = FONTS / "Boldonse-Regular.ttf"  # very wide, heavy display sans
SMALL_FONT = FONTS / "Outfit-Bold.ttf"       # geometric sans for the date

W, H = 3564, 5040  # A3 portrait at 304.8 dpi
MARGIN = 250       # about 21 mm
CONTENT = W - 2 * MARGIN
PAD = 40           # minimum gap between any two printed elements
DATE = ("11.04", "2026")

PAPER = (244, 242, 237)
INK = (24, 22, 26)
DEEP = (176, 0, 108)  # magenta family only, nothing fluorescent
MID = (208, 50, 142)
TINT = (236, 160, 202)
MAUVE = (168, 118, 150)


def font_for_width(path, text, width):
    """Largest font size at which `text` is at most `width` px wide."""
    lo, hi = 8, 3000
    while lo < hi:
        mid = (lo + hi + 1) // 2
        left, _, right, _ = ImageFont.truetype(str(path), mid).getbbox(text)
        if right - left <= width:
            lo = mid
        else:
            hi = mid - 1
    return ImageFont.truetype(str(path), lo)


SMALL = ImageFont.truetype(str(SMALL_FONT), 86)


def measure(font, text):
    left, top, right, bottom = font.getbbox(text)
    return right - left, bottom - top


def catmull_rom(points, spacing=6):
    """Points every ~`spacing` px along a smooth curve through `points`."""
    pts = [points[0], *points, points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1:i + 3]
        steps = max(1, int(math.dist(p1, p2) / spacing))
        for k in range(steps):
            t = k / steps
            out.append(tuple(
                0.5 * (2 * b + (c - a) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (3 * b - a - 3 * c + d) * t ** 3)
                for a, b, c, d in zip(p0, p1, p2, p3)))
    out.append(points[-1])
    return out


def arc(cx, cy, r, start, end, step=2):
    """Points on a circle; angles in degrees, 0 = right, 90 = down."""
    n = max(2, int(abs(end - start) / step))
    return [(cx + r * math.cos(math.radians(start + (end - start) * i / n)),
             cy + r * math.sin(math.radians(start + (end - start) * i / n))) for i in range(n + 1)]


def frac(points):
    """Points given as fractions of the sheet -> pixels."""
    return [(x * W, y * H) for x, y in points]


class Poster:
    """Paper first, then paint, then everything black is printed on top in one pass."""

    def __init__(self, seed):
        self.seed = seed
        rng = random.Random(seed)
        grain = Image.frombytes("L", (W, H), rng.randbytes(W * H)).filter(ImageFilter.GaussianBlur(1.1))
        self.grain = ImageOps.autocontrast(grain, cutoff=1)
        clouds = Image.frombytes("L", (28, 40), rng.randbytes(28 * 40))
        clouds = clouds.resize((W, H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(60))
        self.canvas = Image.new("RGB", (W, H), PAPER)
        self.darken(ImageOps.autocontrast(clouds), 234)  # soft grey mottling in the paper
        self.darken(self.grain, 240)                       # fine paper tooth
        self.tooth = self.grain.point(lambda v: 140 + v * 115 // 255)  # where paint skips the paper
        self.ink = Image.new("L", (W, H), 0)
        self.pen = ImageDraw.Draw(self.ink)
        self.boxes = []

    def darken(self, texture, floor):
        """Multiply the canvas by `texture`, mapped so its darkest value multiplies by floor / 255."""
        t = texture.point(lambda v: floor + v * (255 - floor) // 255)
        self.canvas = ImageChops.multiply(self.canvas, Image.merge("RGB", (t, t, t)))

    def stroke(self, path, width, color, alpha=0.88, dry=0.35, seed=0, bristles=120):
        """Drag a dry brush along `path`: each bristle carries its own paint and runs out on its own."""
        rng = random.Random(self.seed * 1000 + seed)
        pts = catmull_rom(path)
        n = len(pts)
        normals = []
        for i in range(n):
            (x0, y0), (x1, y1) = pts[max(i - 1, 0)], pts[min(i + 1, n - 1)]
            d = math.hypot(x1 - x0, y1 - y0) or 1.0
            normals.append(((y0 - y1) / d, (x1 - x0) / d))
        wobble = rng.uniform(0, 6.3)
        swell = [max(0.08, min(1, i / (n * 0.05)) ** 0.6 * min(1, (n - 1 - i) / (n * 0.25)) ** 0.8
                     * (1 + 0.10 * math.sin(7 * i / n + wobble))) for i in range(n)]
        mask = Image.new("L", (W, H), 0)
        draw = ImageDraw.Draw(mask)

        def lay(run, total):
            if len(run) > 1:
                draw.line(run, fill=round(255 * min(1.0, total / len(run))), width=thick, joint="curve")

        for _ in range(bristles):
            u = rng.uniform(-0.5, 0.5)
            thick = max(3, round(width / bristles * rng.uniform(1.8, 3.4)))
            load = rng.uniform(0.80, 1.05) - 1.4 * dry * u * u  # edge bristles carry less paint
            fade = rng.uniform(0.3, 1.0) * dry                   # paint runs out along the stroke
            f1, f2 = rng.uniform(6, 18), rng.uniform(25, 60)
            p1, p2 = rng.uniform(0, 6.3), rng.uniform(0, 6.3)
            run, total = [], 0.0
            for i, (x, y) in enumerate(pts):
                t = i / (n - 1)
                paint = load - fade * t + 0.35 * dry * (math.sin(f1 * t + p1) + 0.6 * math.sin(f2 * t + p2))
                if paint > 0.42:
                    k = u * width * swell[i]
                    run.append((x + normals[i][0] * k, y + normals[i][1] * k))
                    total += paint
                else:
                    lay(run, total)
                    run, total = [], 0.0
            lay(run, total)
        mask = ImageChops.multiply(mask.filter(ImageFilter.GaussianBlur(2.0)), self.tooth)
        self.canvas.paste(Image.new("RGB", (W, H), color), (0, 0), mask.point(lambda v: round(v * alpha)))

    def claim(self, name, box, inset):
        x0, y0, x1, y1 = box
        if x0 < inset or y0 < inset or x1 > W - inset or y1 > H - inset:
            raise ValueError(f"{name} leaves the page margin: {box}")
        for other, (a0, b0, a1, b1) in self.boxes:
            if x0 < a1 + PAD and a0 < x1 + PAD and y0 < b1 + PAD and b0 < y1 + PAD:
                raise ValueError(f"{name} collides with {other}")
        self.boxes.append((name, box))

    def text(self, text, font, x, y, align="left"):
        """Print `text` with its visible top-left (or, right-aligned, top-right) corner at (x, y)."""
        left, top, right, bottom = font.getbbox(text)
        if align == "right":
            x -= right - left
        self.claim(text, (x, y, x + right - left, y + bottom - top), MARGIN)
        self.pen.text((x - left, y - top), text, font=font, fill=255)
        return right - left, bottom - top

    def text_up(self, text, font, right, bottom):
        """Print `text` reading bottom-to-top, its box ending at (right, bottom)."""
        left, top, r, b = font.getbbox(text)
        tile = Image.new("L", (r - left, b - top), 0)
        ImageDraw.Draw(tile).text((-left, -top), text, font=font, fill=255)
        tile = tile.rotate(90, expand=True)
        x, y = right - tile.width, bottom - tile.height
        self.claim(text, (x, y, right, bottom), MARGIN)
        self.ink.paste(255, (x, y), tile)

    def mark(self, kind, cx, cy):
        r = 27 if kind == "dot" else 33
        self.claim(f"{kind} at {cy}", (cx - r, cy - r, cx + r, cy + r), 60)
        if kind == "dot":
            self.pen.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
        else:
            self.pen.ellipse([cx - r, cy - r, cx + r, cy + r], outline=255, width=7)

    def edge_marks(self, side, marks):
        x = 125 if side == "left" else W - 125
        for y, kind in marks:
            self.mark(kind, x, round(y * H))

    def brackets(self, box, arm=110, width=7):
        x0, y0, x1, y1 = (round(v) for v in box)
        for x, y, sx, sy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
            self.claim("bracket", (min(x, x + sx * arm), min(y, y + sy * arm),
                                   max(x, x + sx * arm), max(y, y + sy * arm)), MARGIN)
            self.pen.line([(x, y + sy * arm), (x, y), (x + sx * arm, y)], fill=255, width=width, joint="curve")

    def save(self, path):
        black = Image.new("RGB", (W, H), INK)
        halo = self.ink.filter(ImageFilter.GaussianBlur(7)).point(lambda v: round(v * 0.28))
        self.canvas.paste(black, (0, 0), halo)  # ink bleeding softly into the paper
        speck = ImageChops.multiply(self.ink, self.grain.point(lambda v: 196 + v * 59 // 255))
        self.canvas.paste(black, (0, 0), speck.filter(ImageFilter.GaussianBlur(0.8)).point(lambda v: round(v * 0.95)))
        self.darken(self.grain, 246)  # one last pass of grain over paint and ink alike
        self.canvas.save(path, dpi=(304.8, 304.8))
        print(f"{path.name}: {self.canvas.width} x {self.canvas.height} px")


def title(p, top, justify=False, align="left", gap=80):
    """BAND over BUSKING. Justified: each word fills the measure; otherwise both share one size."""
    same = font_for_width(TITLE_FONT, "BUSKING", CONTENT)
    x = MARGIN if align == "left" else W - MARGIN
    y = top
    for word in ("BAND", "BUSKING"):
        font = font_for_width(TITLE_FONT, word, CONTENT) if justify else same
        _, h = p.text(word, font, x, y, align)
        y += h + gap
    return y - gap


def date_row(p, y):
    p.text(DATE[0], SMALL, MARGIN, y)
    p.text(DATE[1], SMALL, W - MARGIN, y, "right")


def wave():
    """Sound as a painted wave: layered strokes rolling across the middle of the sheet."""
    p = Poster(1)
    p.stroke(frac([(-0.08, 0.60), (0.18, 0.53), (0.45, 0.63), (0.72, 0.52), (1.08, 0.58)]), 720, TINT, 0.85, 0.25, 1)
    p.stroke(frac([(-0.08, 0.67), (0.22, 0.59), (0.50, 0.70), (0.78, 0.58), (1.08, 0.64)]), 380, MAUVE, 0.55, 0.55, 2)
    p.stroke(frac([(-0.08, 0.63), (0.20, 0.55), (0.48, 0.66), (0.75, 0.54), (1.08, 0.61)]), 470, MID, 0.88, 0.35, 3)
    p.stroke(frac([(-0.05, 0.645), (0.25, 0.575), (0.52, 0.70), (0.80, 0.535), (1.06, 0.60)]), 210, DEEP, 0.92, 0.45, 4)
    date_row(p, title(p, 300, justify=True) + 110)
    p.edge_marks("left", [(0.30, "hoop"), (0.46, "dot"), (0.80, "dot"), (0.92, "hoop")])
    p.edge_marks("right", [(0.27, "dot"), (0.49, "hoop"), (0.83, "hoop"), (0.95, "dot")])
    return p


def ring():
    """The busking circle: a painted ring around an empty stage, framed at its opening."""
    p = Poster(2)
    cx, cy, r = W / 2, 0.61 * H, 0.34 * W
    p.stroke(arc(cx, cy, r + 40, 112, 428), 560, TINT, 0.82, 0.25, 1)
    p.stroke(arc(cx, cy, r - 70, 150, 385), 260, MAUVE, 0.55, 0.6, 2)
    p.stroke(arc(cx, cy, r, 125, 415), 400, MID, 0.88, 0.35, 3)
    p.stroke(arc(cx, cy, r + 15, 205, 400), 190, DEEP, 0.92, 0.45, 4)
    title(p, 300)
    p.brackets((cx - 300, cy + r - 230, cx + 300, cy + r + 150))
    date_row(p, H - MARGIN - measure(SMALL, DATE[1])[1])
    p.edge_marks("left", [(0.22, "dot"), (0.40, "hoop"), (0.70, "dot"), (0.88, "hoop")])
    p.edge_marks("right", [(0.25, "hoop"), (0.52, "dot"), (0.66, "hoop"), (0.90, "dot")])
    return p


def rise():
    """Strokes rising from the street below, thinning as the sound climbs."""
    p = Poster(3)
    p.stroke(frac([(0.30, 1.06), (0.34, 0.86), (0.28, 0.68), (0.36, 0.50), (0.31, 0.36)]), 620, TINT, 0.85, 0.28, 1)
    p.stroke(frac([(0.42, 1.06), (0.45, 0.82), (0.40, 0.62), (0.46, 0.47)]), 300, MAUVE, 0.55, 0.6, 2)
    p.stroke(frac([(0.53, 1.06), (0.49, 0.84), (0.57, 0.64), (0.51, 0.46), (0.56, 0.33)]), 440, MID, 0.88, 0.35, 3)
    p.stroke(frac([(0.70, 1.06), (0.74, 0.88), (0.67, 0.70), (0.72, 0.55), (0.68, 0.44)]), 200, DEEP, 0.92, 0.45, 4)
    title(p, 300)
    p.text_up(f"{DATE[1]}.{DATE[0]}", SMALL, W - MARGIN, H - MARGIN)
    p.edge_marks("left", [(0.24, "dot"), (0.38, "hoop"), (0.62, "dot"), (0.76, "hoop"), (0.93, "dot")])
    return p


def echo():
    """Sound spreading from a corner: four painted arcs, quieter as they travel."""
    p = Poster(4)
    cx, cy = -0.06 * W, 1.04 * H
    for r, width, color, alpha, dry, seed in ((0.40, 300, DEEP, 0.92, 0.35, 1), (0.62, 380, MID, 0.86, 0.40, 2),
                                             (0.84, 520, TINT, 0.78, 0.30, 3), (1.04, 300, MAUVE, 0.50, 0.60, 4)):
        p.stroke(arc(cx, cy, r * W, 262, 368), width, color, alpha, dry, seed)
    date_row(p, title(p, 300, align="right") + 110)
    p.edge_marks("right", [(0.30, "hoop"), (0.44, "dot"), (0.58, "hoop"), (0.80, "dot"), (0.94, "hoop")])
    return p


if __name__ == "__main__":
    for n, make in enumerate((wave, ring, rise, echo), start=1):
        make().save(HERE / f"painted-echo_{n}_{make.__name__}.png")
