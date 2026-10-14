"""Page renderer (PIL) + scan degradation (numpy/cv2). Every element appends a truth record."""
import io
import math
import random
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT_DIRS = ["/usr/share/fonts/opentype/urw-base35", "/usr/share/fonts/truetype/dejavu",
             "/usr/share/fonts/opentype/tlwg", "/usr/share/fonts/opentype/comic-neue",
             "/usr/share/fonts/truetype/liberation", "/usr/share/fonts/opentype/freefont", "C:/Windows/Fonts"]
PRINTED = ["NimbusSans-Regular.otf", "C059-Roman.otf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf", "arial.ttf"]
PRINTED_BOLD = ["NimbusSans-Bold.otf", "C059-Bold.otf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "arialbd.ttf"]
HAND = ["Z003-MediumItalic.otf", "Purisa.otf", "ComicNeue-Italic.otf", "Inkfree.ttf", "segoepr.ttf"]
BASE_DPI = 200
A4 = (int(8.27 * BASE_DPI), int(11.69 * BASE_DPI))


def find_font(names):
    for n in names:
        for d in FONT_DIRS:
            p = Path(d) / n
            if p.exists():
                return str(p)
    raise FileNotFoundError(f"none of {names} found in {FONT_DIRS}")


class Page:
    def __init__(self, rng: random.Random, printed_font=None, hand_font=None, scale=1.0):
        self.r = rng
        self.s = scale
        self.w, self.h = int(A4[0] * scale), int(A4[1] * scale)
        self.img = Image.new("RGB", (self.w, self.h), "white")
        self.d = ImageDraw.Draw(self.img)
        self.m = int(150 * scale)
        self.y = self.m
        self.pf = printed_font or find_font(PRINTED)
        self.pfb = find_font(PRINTED_BOLD)
        self.hf = hand_font or find_font(HAND)
        self.truth: list[dict] = []

    def font(self, px, bold=False):
        return ImageFont.truetype(self.pfb if bold else self.pf, int(px * self.s))

    def _wrap(self, text, font, width):
        lines, cur = [], ""
        for w in text.split():
            t = (cur + " " + w).strip()
            if self.d.textlength(t, font=font) <= width:
                cur = t
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    def room(self, px):
        return self.y + int(px * self.s) < self.h - self.m

    def heading(self, text):
        f = self.font(52, True)
        self.d.text((self.m, self.y), text, font=f, fill="black")
        self.y += int(80 * self.s)
        self.truth.append({"kind": "printed", "text": text})

    def paragraph(self, text, px=33):
        f = self.font(px)
        lh = int(px * 1.4 * self.s)
        lines = self._wrap(text, f, self.w - 2 * self.m)
        shown = []
        for ln in lines:
            if self.y + lh > self.h - self.m:
                break
            self.d.text((self.m, self.y), ln, font=f, fill="black")
            self.y += lh
            shown.append(ln)
        self.y += int(30 * self.s)
        if shown:
            self.truth.append({"kind": "printed", "text": " ".join(shown)})

    def table(self, rows, px=30):
        f, fb = self.font(px), self.font(px, True)
        widths = [0.08, 0.50, 0.14, 0.28]
        W = self.w - 2 * self.m
        xs = [self.m]
        for fr in widths:
            xs.append(xs[-1] + int(W * fr))
        rh = int(px * 1.9 * self.s)
        y0 = self.y
        for ri, row in enumerate(rows):
            for ci, cell in enumerate(row):
                fnt = fb if ri == 0 else f
                tx = xs[ci] + int(10 * self.s)
                if ci == 3:  # right-align amounts
                    tx = xs[ci + 1] - int(10 * self.s) - int(self.d.textlength(cell, font=fnt))
                self.d.text((tx, self.y + int(10 * self.s)), cell, font=fnt, fill="black")
            self.y += rh
        for i in range(len(rows) + 1):
            yy = y0 + i * rh
            self.d.line([(xs[0], yy), (xs[-1], yy)], fill="black", width=max(1, int(2 * self.s)))
        for x in xs:
            self.d.line([(x, y0), (x, y0 + len(rows) * rh)], fill="black", width=max(1, int(2 * self.s)))
        self.y += int(40 * self.s)
        self.truth.append({"kind": "table", "rows": rows, "text": "\n".join(" ".join(r) for r in rows)})

    def picture(self, h_frac=0.14):
        """Synthetic photo-like image: must produce NO text. Engines that read text into it hallucinate."""
        W = self.w - 2 * self.m
        H = int(self.h * h_frac)
        rng = np.random.default_rng(self.r.randint(0, 2**31))
        gx, gy = np.meshgrid(np.linspace(0, 1, W // 4), np.linspace(0, 1, H // 4))
        c = [rng.uniform(40, 200, 3) for _ in range(3)]
        arr = (gx[..., None] * c[0] + gy[..., None] * c[1] + (1 - gx[..., None]) * c[2]) / 1.6
        for _ in range(8):  # blobs
            cx, cy = rng.uniform(0, W // 4), rng.uniform(0, H // 4)
            rad = rng.uniform(8, 40)
            yy, xx = np.ogrid[:H // 4, :W // 4]
            m = ((xx - cx) ** 2 + (yy - cy) ** 2) < rad ** 2
            arr[m] = rng.uniform(20, 230, 3)
        arr += rng.normal(0, 6, arr.shape)
        im = Image.fromarray(np.clip(arr, 0, 255).astype("uint8")).resize((W, H), Image.BICUBIC)
        self.img.paste(im, (self.m, self.y))
        self.y += H + int(30 * self.s)
        self.truth.append({"kind": "image", "text": ""})

    def handwritten(self, label, value, px=58, ink=(25, 30, 90)):
        """Printed label + handwriting-like value (per-glyph jitter on a script font)."""
        lf = self.font(32)
        self.d.text((self.m, self.y), label, font=lf, fill="black")
        x = self.m + int(self.d.textlength(label, font=lf)) + int(30 * self.s)
        layer = Image.new("L", (self.w, int(px * 2.4 * self.s)), 0)
        ld = ImageDraw.Draw(layer)
        hf = ImageFont.truetype(self.hf, int(px * self.s))
        cx = x
        for ch in value:
            adv = ld.textlength(ch, font=hf)
            if ch != " ":
                g = Image.new("L", (int(px * 2 * self.s), int(px * 2 * self.s)), 0)
                ImageDraw.Draw(g).text((int(px * 0.4 * self.s), int(px * 0.3 * self.s)), ch, font=hf, fill=255)
                g = g.rotate(self.r.uniform(-9, 9), resample=Image.BICUBIC)
                s = self.r.uniform(0.88, 1.12)
                g = g.resize((int(g.width * s), int(g.height * s)))
                layer.paste(255, (int(cx - px * 0.4 * self.s), int(self.r.uniform(-4, 6) * self.s)), g)
            cx += adv * self.r.uniform(1.0, 1.12)
        layer = layer.filter(ImageFilter.GaussianBlur(0.8 * self.s))
        colour = Image.new("RGB", layer.size, ink)
        self.img.paste(colour, (0, self.y - int(px * 0.5 * self.s)), layer)
        self.d.line([(x - 10, self.y + int(52 * self.s)), (min(cx + 40, self.w - self.m), self.y + int(52 * self.s))],
                    fill=(120, 120, 120), width=max(1, int(2 * self.s)))
        self.y += int(105 * self.s)
        self.truth.append({"kind": "printed", "text": label})
        self.truth.append({"kind": "handwritten", "text": value})

    def skip(self, px):
        self.y += int(px * self.s)


def degrade(img: Image.Image, rng: random.Random, level: str) -> Image.Image:
    """level: 'clean' | 'scan' (typical office scan) | 'bad' (fax-like / poor)."""
    a = np.array(img)
    if level == "clean":
        return img
    nprng = np.random.default_rng(rng.randint(0, 2**31))
    amp = {"scan": 1.0, "bad": 2.0}[level]
    h, w = a.shape[:2]
    ang = rng.uniform(-1.2, 1.2) * amp
    M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
    a = cv2.warpAffine(a, M, (w, h), borderValue=(255, 255, 255), flags=cv2.INTER_LINEAR)
    k = 3 if level == "scan" else 5
    a = cv2.GaussianBlur(a, (k, k), 0)
    f = a.astype(np.float32)
    # contrast loss + uneven illumination
    f = 255 - (255 - f) * rng.uniform(0.75, 0.95) / (1 if level == "scan" else 1.2)
    gx = np.linspace(rng.uniform(0.9, 1), rng.uniform(0.85, 1), w)[None, :, None]
    f *= gx
    f += nprng.normal(0, 7 * amp, f.shape)
    # speckles
    n = int(w * h * 0.00005 * amp)
    ys, xs = nprng.integers(0, h, n), nprng.integers(0, w, n)
    f[ys, xs] = nprng.integers(0, 120, (n, 1))
    out = Image.fromarray(np.clip(f, 0, 255).astype("uint8"))
    return out


def to_jpeg(img: Image.Image, dpi: int, quality: int) -> bytes:
    """Page images are rendered at their target dpi already (see build_doc scale)."""
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality, dpi=(dpi, dpi))
    return buf.getvalue()
