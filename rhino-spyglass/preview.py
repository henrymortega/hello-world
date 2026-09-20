"""3/4-view preview of the stylized spyglass."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

import params as P

OUT = Path(__file__).resolve().parent / "preview.png"


def proj(x, y, z):
    sx = 0.82 * x + 0.48 * z
    sy = -0.40 * x + 0.86 * y + 0.16 * z
    return sx, sy


def circle_pts(x, r, n=48):
    return [proj(x, r * math.cos(a), r * math.sin(a)) for a in [2 * math.pi * i / n for i in range(n)]]


def to_px(pts, bounds, size, pad=0.14):
    minx, miny, maxx, maxy = bounds
    out = []
    for sx, sy in pts:
        px = int((sx - minx) / (maxx - minx) * (1 - 2 * pad) * size + pad * size)
        py = int((sy - miny) / (maxy - miny) * (1 - 2 * pad) * size + pad * size)
        out.append((px, py))
    return out


def shade(rgb, k):
    return tuple(max(0, min(255, int(c * k))) for c in rgb)


def draw_cyl(draw, x0, x1, r0, r1, rgb, bounds, size, hole_r=None):
    n = 40
    # body as strips around the circumference, back faces first
    strips = []
    for i in range(n):
        a0 = 2 * math.pi * i / n
        a1 = 2 * math.pi * (i + 1) / n
        y0, z0 = r0 * math.cos(a0), r0 * math.sin(a0)
        y1, z1 = r0 * math.cos(a1), r0 * math.sin(a1)
        y2, z2 = r1 * math.cos(a1), r1 * math.sin(a1)
        y3, z3 = r1 * math.cos(a0), r1 * math.sin(a0)
        mid_z = 0.25 * (z0 + z1 + z2 + z3)
        # lighting from upper-left
        ny = math.cos((a0 + a1) * 0.5)
        nz = math.sin((a0 + a1) * 0.5)
        lit = 0.55 + 0.45 * max(0.0, ny * 0.3 + nz * 0.2 + 0.5)
        strips.append((mid_z, [(x0, y0, z0), (x0, y1, z1), (x1, y2, z2), (x1, y3, z3)], lit))
    strips.sort(key=lambda s: s[0])
    for _, quad, lit in strips:
        draw.polygon(to_px([proj(*p) for p in quad], bounds, size), fill=shade(rgb, lit))
    # front cap
    cap = circle_pts(x1, r1, n)
    draw.polygon(to_px(cap, bounds, size), fill=shade(rgb, 0.72))
    if hole_r:
        hole = circle_pts(x1 + 0.2, hole_r, n)
        draw.polygon(to_px(hole, bounds, size), fill=(32, 186, 230) if hole_r == P.LENS_R else shade(rgb, 0.35))


def render(size=1000):
    samples = []
    for x, r in (
        (P.EYE_X, P.EYE_R),
        (P.EYE_X + P.EYE_L, P.EYE_R),
        (P.SILVER_X, P.SILVER_R),
        (P.BARREL_X1, P.BARREL_R1),
        (P.RIM_X + P.RIM_L, P.RIM_R_OUT),
        (P.LENS_X + P.LENS_L, P.LENS_R),
        (P.SIGHT_X1, P.SIGHT_Y1),
    ):
        samples.extend(circle_pts(x, r if r < 80 else 30))
    samples.append(proj(P.SIGHT_X0, P.SIGHT_Y1, P.SIGHT_Z0))
    samples.append(proj(P.SIGHT_X1, P.SIGHT_Y1, P.SIGHT_Z1))
    xs = [p[0] for p in samples]
    ys = [p[1] for p in samples]
    bounds = (min(xs), min(ys), max(xs), max(ys))

    img = Image.new("RGB", (size, size), (200, 200, 204))
    draw = ImageDraw.Draw(img)

    draw_cyl(draw, P.EYE_X, P.EYE_X + P.EYE_L, P.EYE_R, P.EYE_R, P.GOLD[:3], bounds, size)
    draw_cyl(draw, P.SILVER_X, P.SILVER_X + P.SILVER_L, P.SILVER_R, P.SILVER_R, P.CHROME[:3], bounds, size)
    draw_cyl(draw, P.COLLAR_X, P.COLLAR_X + P.COLLAR_L, P.COLLAR_R, P.COLLAR_R, P.COLLAR[:3], bounds, size)
    draw_cyl(draw, P.BARREL_X0, P.BARREL_X1, P.BARREL_R0, P.BARREL_R1, P.WOOD[:3], bounds, size)
    draw_cyl(
        draw,
        P.RIM_X,
        P.RIM_X + P.RIM_L,
        P.RIM_R_OUT,
        P.RIM_R_OUT,
        P.WOOD_DARK[:3],
        bounds,
        size,
        hole_r=P.LENS_R,
    )
    # sight box
    x0, x1 = P.SIGHT_X0, P.SIGHT_X1
    y0, y1 = P.SIGHT_Y0, P.SIGHT_Y1
    z0, z1 = P.SIGHT_Z0, P.SIGHT_Z1
    faces = [
        ([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], 1.08),
        ([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], 0.78),
        ([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], 0.9),
    ]
    for quad, k in faces:
        draw.polygon(to_px([proj(*p) for p in quad], bounds, size), fill=shade(P.WOOD[:3], k), outline=(110, 70, 25))
    return img


if __name__ == "__main__":
    render().save(OUT)
    print("wrote", OUT)
