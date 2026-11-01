"""Band busking - poster with a cut-out guitar photo (week 2).

Photo: Apolo Photographer on Unsplash (Unsplash License) -> week2/photos/guitar.jpg
A3 portrait, 3564 x 5040 px (304.8 dpi).

Run from the class folder (in the Claude app, keep uv's Python out of AppData):
    $env:UV_PYTHON_INSTALL_DIR = 'C:\\design-class\\.claude\\uv\\python'
    $env:UV_CACHE_DIR = 'C:\\design-class\\.claude\\uv\\cache'
    uv run --with pillow week2/make_guitar_poster.py
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
FONTS = HERE.parent / ".claude" / "skills" / "canvas-design" / "canvas-fonts"
TYPE_FONT = FONTS / "PoiretOne-Regular.ttf"  # light Art Deco display face
PHOTO = HERE / "photos" / "guitar.jpg"
CUTOUT = HERE / "photos" / "guitar_cutout.png"
OUT = HERE / "band-busking_guitar.png"

W, H = 3564, 5040  # A3 portrait at 304.8 dpi
PAPER = (248, 246, 241)
MAGENTA = (190, 8, 118)  # deep ink magenta, not fluorescent
BLACK = (24, 20, 24)


def ink_box(font, text, anchor):
    """Tight box around the ink of `text` (not its side bearings), relative to the anchor point."""
    left, top, right, bottom = font.getbbox(text, anchor=anchor)
    pad = font.size
    tile = Image.new("L", (right - left + 2 * pad, bottom - top + 2 * pad), 0)
    ImageDraw.Draw(tile).text((pad - left, pad - top), text, font=font, fill=255, anchor=anchor)
    x0, y0, x1, y1 = tile.getbbox()
    return x0 - pad + left, y0 - pad + top, x1 - pad + left, y1 - pad + top


def font_for_width(text, width):
    """Largest size at which the ink of `text` is at most `width` px wide."""
    lo, hi = 8, 4000
    while lo < hi:
        mid = (lo + hi + 1) // 2
        x0, _, x1, _ = ink_box(ImageFont.truetype(str(TYPE_FONT), mid), text, "ls")
        if x1 - x0 <= width:
            lo = mid
        else:
            hi = mid - 1
    return ImageFont.truetype(str(TYPE_FONT), lo)


def set_text(draw, text, font, x, baseline, align="left"):
    """Set `text` on `baseline`, its ink starting (or, right-aligned, ending) exactly at x."""
    anchor = "ls" if align == "left" else "rs"
    x0, top, x1, _ = ink_box(font, text, anchor)
    draw.text((x - (x0 if align == "left" else x1), baseline), text, font=font, fill=255, anchor=anchor)
    return -top  # height of the ink above the baseline


def extremes(img):
    """Per-pixel brightest and darkest channel of an RGB image."""
    r, g, b = img.split()
    return ImageChops.lighter(ImageChops.lighter(r, g), b), ImageChops.darker(ImageChops.darker(r, g), b)


def backdrop(img):
    """Estimate the empty studio backdrop: border colours spread across, guitar painted out, blurred."""
    small = img.resize((img.width // 8, img.height // 8), Image.Resampling.BOX)
    w, h = small.size
    edges = Image.new("RGB", (2, h))
    edges.paste(small.crop((2, 0, 30, h)).resize((1, h), Image.Resampling.BOX), (0, 0))
    edges.paste(small.crop((w - 18, 0, w - 2, h)).resize((1, h), Image.Resampling.BOX), (1, 0))
    rows = edges.resize((w, h), Image.Resampling.BILINEAR)
    differs, _ = extremes(ImageChops.difference(small, rows))
    guitar = differs.point(lambda v: 255 if v > 22 else 0).filter(ImageFilter.MaxFilter(9))
    empty = Image.composite(rows, small, guitar)
    return empty.filter(ImageFilter.GaussianBlur(10)).resize(img.size, Image.Resampling.BICUBIC)


def cut_out(img):
    """Separate the guitar from the grey backdrop and its floor shadow; returns a cropped RGBA image."""
    differs, _ = extremes(ImageChops.difference(img, backdrop(img)))
    fg = differs.point(lambda v: 255 if v > 28 else 0)
    hi, lo = extremes(img)
    grey = ImageChops.difference(hi, lo).point(lambda v: 255 if v < 20 else 0)
    midtone = img.convert("L").point(lambda v: 255 if 90 < v < 215 else 0)
    floor = Image.new("L", img.size, 0)
    ImageDraw.Draw(floor).rectangle([0, 2700, img.width, img.height], fill=255)
    shadow = ImageChops.multiply(ImageChops.multiply(grey, midtone), floor)
    fg = ImageChops.subtract(fg, shadow).filter(ImageFilter.MedianFilter(5))
    # Work out the silhouette at quarter size: an opening drops slivers thinner than ~36 px (the dark
    # contact shadow, the strap button), and anything the outside backdrop cannot reach is guitar.
    quarter = fg.resize((img.width // 4, img.height // 4), Image.Resampling.BOX).point(lambda v: 255 if v > 127 else 0)
    reach = quarter.filter(ImageFilter.MinFilter(9)).filter(ImageFilter.MaxFilter(9))
    ImageDraw.floodfill(reach, (0, 0), 128)  # 128 = outside, 255 = guitar, 0 = enclosed (chrome, inlays)

    def full(mask):
        return mask.resize(img.size, Image.Resampling.BILINEAR).point(lambda v: 255 if v > 127 else 0)

    inside = full(reach.point(lambda v: 0 if v == 128 else 255).filter(ImageFilter.MaxFilter(5)))
    holes = full(reach.point(lambda v: 255 if v == 0 else 0))
    alpha = ImageChops.multiply(inside, ImageChops.lighter(fg, holes))
    alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
    cut = img.convert("RGBA")
    cut.putalpha(alpha)
    return cut.crop(alpha.getbbox())


# How much of each ink a grey value gets: magenta carries the mid-tones, black only the shadows.
MAGENTA_INK = [round(255 * min(1, max(0, (0.92 - v / 255) / 0.80)) ** 0.9) for v in range(256)]
BLACK_INK = [round(255 * min(1, max(0, (0.42 - v / 255) / 0.40)) ** 1.2) for v in range(256)]


def halftone(coverage, cell, angle):
    """Round halftone dots on a screen turned by `angle` degrees; dot area follows coverage (0-255)."""
    average = coverage.filter(ImageFilter.BoxBlur(cell / 2)).load()
    w, h = coverage.size
    ss = 2  # draw at twice the size, then shrink, for smooth dot edges
    dots = Image.new("L", (w * ss, h * ss), 0)
    draw = ImageDraw.Draw(dots)
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    reach = int(math.hypot(w, h) / cell / 2) + 2
    for i in range(-reach, reach + 1):
        for j in range(-reach, reach + 1):
            x, y = w / 2 + (i * c - j * s) * cell, h / 2 + (i * s + j * c) * cell
            if not (0 <= x < w and 0 <= y < h):
                continue
            ink = average[int(x), int(y)] / 255
            if ink < 0.02:
                continue
            # Dot area = coverage until neighbours touch (78.5 %), then grow to close the gaps.
            r = cell * (math.sqrt(ink / math.pi) if ink < 0.785 else 0.5 + (ink - 0.785) / 0.215 * 0.21)
            draw.ellipse([(x - r) * ss, (y - r) * ss, (x + r) * ss, (y + r) * ss], fill=255)
    return dots.resize((w, h), Image.Resampling.LANCZOS)


def ink(canvas, mask, color, grain, alpha=0.95):
    """Print `mask` onto the canvas in one ink, with a slightly worn edge."""
    worn = ImageChops.multiply(mask, grain.point(lambda v: 170 + v * 85 // 255))
    worn = worn.filter(ImageFilter.GaussianBlur(0.7)).point(lambda v: round(v * alpha))
    canvas.paste(Image.new("RGB", (W, H), color), (0, 0), worn)


class Press:
    """One ink: collect marks on a mask, then print them in one go."""

    def __init__(self):
        self.mask = Image.new("L", (W, H), 0)
        self.draw = ImageDraw.Draw(self.mask)

    def print_on(self, canvas, color, grain):
        ink(canvas, self.mask, color, grain)


def paper(rng):
    grain = Image.frombytes("L", (W, H), rng.randbytes(W * H)).filter(ImageFilter.GaussianBlur(1.0))
    grain = ImageOps.autocontrast(grain, cutoff=1)
    t = grain.point(lambda v: 240 + v * 15 // 255)
    canvas = ImageChops.multiply(Image.new("RGB", (W, H), PAPER), Image.merge("RGB", (t, t, t)))
    draw = ImageDraw.Draw(canvas)
    for _ in range(240):  # flecks in the paper
        x, y, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1.5, 4.5)
        shade = rng.randint(150, 215)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(shade, shade - 2, shade - 4))
    return canvas, grain


def orbit(cx, cy, rx, ry, tilt, start, end):
    """Points along a tilted elliptical arc; angles in degrees, 90 = nearest the viewer."""
    c, s = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
    points = []
    for i in range(721):
        t = math.radians(start + (end - start) * i / 720)
        x, y = rx * math.cos(t), ry * math.sin(t)
        points.append((cx + x * c - y * s, cy + x * s + y * c))
    return points


def poster():
    rng = random.Random(1104)
    canvas, grain = paper(rng)
    behind, black = Press(), Press()

    # Type in a light Art Deco face: BAND across the top (its foot just behind the guitar body),
    # BUSKING low on the left, the date low on the right, both sitting on one baseline.
    left, right, baseline = round(0.055 * W), round(0.945 * W), round(0.925 * H)
    band = font_for_width("BAND", right - left)
    band_baseline = left - ink_box(band, "BAND", "ls")[1]  # the same white margin above as at the sides
    set_text(behind.draw, "BAND", band, left, band_baseline)
    set_text(behind.draw, "BUSKING", font_for_width("BUSKING", round(0.352 * W)), left, baseline)
    day = font_for_width("11.04", round(0.284 * W))
    day_h = set_text(black.draw, "11.04", day, right, baseline, "right")
    year = ImageFont.truetype(str(TYPE_FONT), day.size // 2)
    set_text(black.draw, "2026/", year, right, baseline - day_h - round(0.012 * H), "right")

    # The guitar, upside down: its body where the reference has the candy, its neck as the stick.
    cut = cut_out(Image.open(PHOTO).convert("RGB"))
    cut.save(CUTOUT)
    guitar = cut.rotate(184.5, resample=Image.Resampling.BICUBIC, expand=True)  # the photo leans ~3 deg
    scale = 0.80 * H / guitar.height
    guitar = guitar.resize((round(guitar.width * scale), round(guitar.height * scale)), Image.Resampling.LANCZOS)
    gx, gy = round(W / 2 - guitar.width / 2), band_baseline - round(0.01 * H)  # body just over BAND's feet
    alpha = guitar.getchannel("A")
    solid = alpha.point(lambda v: 255 if v > 128 else 0)
    fade = Image.linear_gradient("L").resize(guitar.size)  # 0 at top, 255 at bottom
    fade = fade.point(lambda v: 255 if v < 150 else round(255 - (v - 150) * 1.55))  # the neck thins out

    # Two-ink halftone: magenta dots for the mid-tones, black dots on top for the shadows.
    grey = ImageOps.autocontrast(guitar.convert("L"), cutoff=(1, 0.5), mask=solid)
    presence = ImageChops.multiply(alpha, fade)
    magenta_dots = halftone(ImageChops.multiply(grey.point(MAGENTA_INK), presence), 20, 75)
    black_dots = halftone(ImageChops.multiply(grey.point(BLACK_INK), presence), 20, 45)

    def on_sheet(layer):
        sheet = Image.new("L", (W, H), 0)
        sheet.paste(layer, (gx, gy))
        return sheet

    body = alpha.crop((0, 0, guitar.width, round(guitar.height * 0.42))).getbbox()
    cx, cy = gx + (body[0] + body[2]) / 2, gy + (body[1] + body[3]) / 2
    # A ring around the body, open at the front so it only ever passes behind the guitar.
    ring = orbit(cx, cy, 0.42 * W, 0.075 * H, -10, 150, 400)
    behind.draw.line(ring, fill=255, width=6, joint="curve")
    for x, y in (ring[0], ring[len(ring) * 85 // 250], ring[-1]):  # both ends, and one at 235 degrees
        behind.draw.ellipse([x - 15, y - 15, x + 15, y + 15], fill=255)

    blank = canvas.copy()
    behind.print_on(canvas, MAGENTA, grain)
    black.print_on(canvas, BLACK, grain)
    canvas.paste(blank, (0, 0), on_sheet(ImageChops.multiply(solid, fade)))  # knock out what the guitar covers
    ink(canvas, on_sheet(ImageChops.multiply(magenta_dots, alpha)), MAGENTA, grain)
    ink(canvas, on_sheet(ImageChops.multiply(black_dots, alpha)), BLACK, grain)
    t = grain.point(lambda v: 246 + v * 9 // 255)  # one pass of grain over photo and ink alike
    canvas = ImageChops.multiply(canvas, Image.merge("RGB", (t, t, t)))
    canvas.save(OUT, dpi=(304.8, 304.8))
    print(f"{OUT.name}: {canvas.width} x {canvas.height} px; guitar {guitar.width} x {guitar.height} at {gx}, {gy}")


if __name__ == "__main__":
    poster()
