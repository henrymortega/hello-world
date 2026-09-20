"""High bird's-eye preview of the tube field and silk-fold waves."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

import params as P
from field import field_size, iter_tubes, wave_bounds, wave_z

OUT = Path(__file__).resolve().parent / "preview.png"


def cam(x: float, y: float, z: float) -> tuple[float, float]:
    """High angle, slight yaw — closer to the reference photograph."""
    ang = 0.22
    xr = x * math.cos(ang) - y * math.sin(ang)
    yr = x * math.sin(ang) + y * math.cos(ang)
    sx = xr + 0.12 * yr
    sy = -0.62 * yr - 0.38 * z
    return sx, sy


def world_to_px(x: float, y: float, z: float, bounds, size: int) -> tuple[int, int]:
    sx, sy = cam(x, y, z)
    minx, miny, maxx, maxy = bounds
    pad = 0.07
    w = maxx - minx
    h = maxy - miny
    px = int((sx - minx) / w * (1 - 2 * pad) * size + pad * size)
    py = int((sy - miny) / h * (1 - 2 * pad) * size + pad * size)
    return px, py


def compute_bounds() -> tuple[float, float, float, float]:
    w, d = field_size()
    x0, x1, y0, y1 = wave_bounds()
    samples = []
    for x, y, z in (
        (-w * 0.5, -d * 0.5, 0),
        (w * 0.5, -d * 0.5, 0),
        (-w * 0.5, d * 0.5, P.MAX_HEIGHT),
        (w * 0.5, d * 0.5, P.MAX_HEIGHT),
        (x0, y0, 0),
        (x1, y0, P.WAVE_AMP),
        (x0, y1, P.WAVE_AMP),
        (x1, y1, P.WAVE_AMP * 1.4),
    ):
        samples.append(cam(x, y, z))
    xs = [s[0] for s in samples]
    ys = [s[1] for s in samples]
    return min(xs), min(ys), max(xs), max(ys)


def wave_normal(x: float, y: float) -> tuple[float, float, float]:
    e = 3.0
    dx = wave_z(x + e, y) - wave_z(x - e, y)
    dy = wave_z(x, y + e) - wave_z(x, y - e)
    nx, ny, nz = -dx / (2 * e), -dy / (2 * e), 1.0
    mag = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / mag, ny / mag, nz / mag


def shade_wave(x: float, y: float) -> tuple[int, int, int]:
    nx, ny, nz = wave_normal(x, y)
    # key light from upper-right
    lx, ly, lz = 0.35, 0.15, 0.92
    lm = math.sqrt(lx * lx + ly * ly + lz * lz)
    ndotl = max(0.0, (nx * lx + ny * ly + nz * lz) / lm)
    # tight highlight so folds read as silk
    spec = ndotl ** 7
    t = 0.06 + 0.72 * ndotl + 0.22 * spec
    if t < 0.45:
        u = t / 0.45
        c = int(12 + 40 * u)
        return (c, c, c + 2)
    u = (t - 0.45) / 0.55
    c = int(48 + 200 * (u ** 0.85))
    return (min(c, 250), min(c, 250), min(c + 4, 252))


def draw_waves(draw: ImageDraw.ImageDraw, bounds, size: int) -> None:
    x0, x1, y0, y1 = wave_bounds()
    nu, nv = 90, 70
    pts = []
    for i in range(nu):
        x = x0 + (x1 - x0) * i / (nu - 1)
        row = []
        for j in range(nv):
            y = y0 + (y1 - y0) * j / (nv - 1)
            row.append((x, y, wave_z(x, y)))
        pts.append(row)

    quads = []
    for i in range(nu - 1):
        for j in range(nv - 1):
            a = pts[i][j]
            depth = a[0] * 0.2 + a[1]
            quads.append((depth, i, j))
    quads.sort(key=lambda q: q[0])

    for _, i, j in quads:
        a, b = pts[i][j], pts[i + 1][j]
        c, d = pts[i + 1][j + 1], pts[i][j + 1]
        poly = [
            world_to_px(a[0], a[1], a[2], bounds, size),
            world_to_px(b[0], b[1], b[2], bounds, size),
            world_to_px(c[0], c[1], c[2], bounds, size),
            world_to_px(d[0], d[1], d[2], bounds, size),
        ]
        mx = (a[0] + c[0]) * 0.5
        my = (a[1] + c[1]) * 0.5
        draw.polygon(poly, fill=shade_wave(mx, my))


def draw_tubes(draw: ImageDraw.ImageDraw, bounds, size: int) -> None:
    tubes = list(iter_tubes())
    tubes.sort(key=lambda t: t[1])  # far (high y) first
    wspan = bounds[2] - bounds[0]
    r_px = max(2.2, P.TUBE_OUTER_R / wspan * size * 1.15)
    r_in = r_px * (P.TUBE_INNER_R / P.TUBE_OUTER_R)

    for x, y, z, is_dot in tubes:
        tx, ty = world_to_px(x, y, z, bounds, size)
        if is_dot:
            rr = max(1, int(r_px * 0.35))
            draw.ellipse((tx - rr, ty - rr * 0.72, tx + rr, ty + rr * 0.72), fill=(16, 78, 36))
            continue

        # short shaft so height reads without turning into an isometric forest
        bx, by = world_to_px(x, y, 0.0, bounds, size)
        draw.line((bx, by, tx, ty), fill=(24, 118, 58), width=max(2, int(r_px * 1.2)))
        rx, ry = r_px, r_px * 0.72
        draw.ellipse((tx - rx, ty - ry, tx + rx, ty + ry), fill=(48, 178, 90), outline=(16, 88, 42))
        if r_in > 1.1:
            ix, iy = r_in, r_in * 0.72
            draw.ellipse((tx - ix, ty - iy, tx + ix, ty + iy), fill=(10, 42, 22))


def render(size: int = 1100) -> Image.Image:
    bounds = compute_bounds()
    img = Image.new("RGB", (size, size), (232, 232, 236))
    draw = ImageDraw.Draw(img)
    draw_waves(draw, bounds, size)
    draw_tubes(draw, bounds, size)
    return img


if __name__ == "__main__":
    im = render()
    im.save(OUT)
    print(f"wrote {OUT}  tubes={len(list(iter_tubes()))}")
