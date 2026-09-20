"""Render a 2D front-view preview of the scale pendant for visual matching."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

import params as P
from lattice import cell_centers, fade_scale

OUT = Path(__file__).resolve().parent / "preview_front.png"


def np_smoothstep(t: np.ndarray) -> np.ndarray:
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def rounded_rect_sdf(x: np.ndarray, y: np.ndarray, w: float, h: float, r: float) -> np.ndarray:
    qx = np.abs(x) - (w * 0.5 - r)
    qy = np.abs(y) - (h * 0.5 - r)
    outside = np.sqrt(np.maximum(qx, 0.0) ** 2 + np.maximum(qy, 0.0) ** 2)
    inside = np.minimum(np.maximum(qx, qy), 0.0)
    return outside + inside - r


def superellipse_sdf(
    x: np.ndarray, y: np.ndarray, cx: float, cy: float, rx: float, ry: float, n: float
) -> np.ndarray:
    dx = np.abs(x - cx) / max(rx, 1e-6)
    dy = np.abs(y - cy) / max(ry, 1e-6)
    return (np.power(dx, n) + np.power(dy, n)) ** (1.0 / n) - 1.0


def render(size: int = 900) -> Image.Image:
    pad = 70
    span = max(P.WIDTH, P.HEIGHT) + pad * 2
    res = size
    px = span / res

    xs = (np.arange(res) + 0.5) * px - span * 0.5
    ys = span * 0.5 - (np.arange(res) + 0.5) * px
    X, Y = np.meshgrid(xs, ys)

    body = rounded_rect_sdf(X, Y, P.WIDTH, P.HEIGHT, P.CORNER_RADIUS)
    inside = body < 0

    hole = np.full(X.shape, 1.0, dtype=np.float64)
    rim = np.full(X.shape, 1.0, dtype=np.float64)
    for cx, cy in cell_centers():
        s = fade_scale(cy)
        if s < 0.06:
            continue
        rx = 0.5 * P.CELL_W * s
        ry = 0.5 * P.CELL_H * s
        sdf = superellipse_sdf(X, Y, cx, cy, rx, ry, P.SUPERELLIPSE_N)
        hole = np.minimum(hole, sdf)
        rim = np.minimum(rim, superellipse_sdf(X, Y, cx, cy, rx * 1.22, ry * 1.16, P.SUPERELLIPSE_N))

    through = inside & (hole < 0) & (Y > (-P.HEIGHT * 0.5 + P.BOTTOM_SOLID * 0.15))
    metal = inside & ~through

    ny = (Y - (-P.HEIGHT * 0.5)) / P.HEIGHT
    base = 0.22 + 0.55 * np.clip(ny, 0, 1)
    lip = np_smoothstep((0.08 - ny) / 0.08)
    shade = base * (1.0 - 0.55 * lip)
    shade = shade + 0.08 * (X / (P.WIDTH * 0.5))
    shade = np.clip(shade, 0.05, 0.95)

    hole_depth = np.clip(-hole, 0, 1)
    interior = 0.04 + 0.12 * hole_depth
    rim_band = (rim < 0) & (hole > 0) & inside

    rgb = np.zeros((res, res, 3), dtype=np.float64)
    bg = 0.78 + 0.08 * np.linspace(0, 1, res)[:, None]
    rgb[..., 0] = bg
    rgb[..., 1] = bg
    rgb[..., 2] = bg + 0.02

    metal_col = np.stack([shade, shade, shade * 0.98], axis=-1)
    rgb[metal] = metal_col[metal]
    rgb[through] = np.stack([interior, interior * 0.95, interior * 0.9], axis=-1)[through]
    rgb[rim_band] = np.clip(rgb[rim_band] + 0.28, 0, 1)

    hx, hy = 0.0, P.HEIGHT * 0.5 + P.HANGER_SPHERE_R * 0.15
    sphere = (X - hx) ** 2 + (Y - hy) ** 2 <= P.HANGER_SPHERE_R**2
    stem = (np.abs(X - hx) <= P.STEM_R) & (Y >= hy) & (Y <= hy + P.STEM_H)
    rgb[sphere | stem] = (0.55, 0.55, 0.58)

    return Image.fromarray(np.clip(rgb * 255, 0, 255).astype(np.uint8), mode="RGB")


if __name__ == "__main__":
    im = render()
    im.save(OUT)
    print(f"wrote {OUT}")
