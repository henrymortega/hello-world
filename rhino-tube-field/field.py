"""Scalar field that drives tube height, presence, and the striped waves."""

from __future__ import annotations

import math
from typing import Iterator, List, Tuple

import params as P

Point3 = Tuple[float, float, float]


def field_size() -> Tuple[float, float]:
    return (P.COLS - 1) * P.PITCH, (P.ROWS - 1) * P.PITCH


def smoothstep(t: float) -> float:
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    return t * t * (3.0 - 2.0 * t)


def _hash01(i: int, j: int) -> float:
    n = (i * 374761393 + j * 668265263) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return (n & 0xFFFFFF) / float(0xFFFFFF)


def _ellipse_sdf(nx: float, ny: float, cx: float, cy: float, rx: float, ry: float) -> float:
    return math.hypot((nx - cx) / rx, (ny - cy) / ry) - 1.0


def _land_sdf(nx: float, ny: float) -> float:
    """Negative inside the green 'continent' on the left."""
    d = _ellipse_sdf(nx, ny, 0.28, 0.50, 0.52, 0.70)
    d = min(d, _ellipse_sdf(nx, ny, 0.42, 0.28, 0.28, 0.34))
    d = min(d, _ellipse_sdf(nx, ny, 0.18, 0.82, 0.26, 0.26))
    d = min(d, _ellipse_sdf(nx, ny, 0.48, 0.62, 0.18, 0.22))
    coast = 0.05 * math.sin(nx * 25.0 + ny * 18.0) + 0.03 * math.sin(nx * 12.0 - ny * 22.0)
    coast += 0.018 * math.sin(nx * 39.0 + ny * 8.0)
    return d + coast


def _river(nx: float, ny: float) -> float:
    """0 on a winding gap, 1 far from it."""
    path = ny - (0.52 + 0.10 * math.sin(nx * 6.4) + 0.05 * math.sin(nx * 2.7 + 0.8))
    path2 = (0.55 * nx + ny) - 0.92
    r1 = 1.0 - smoothstep(abs(path) / 0.075)
    r2 = 1.0 - smoothstep(abs(path2) / 0.055)
    return max(r1, r2 * 0.85)


def tube_origin(col: int, row: int) -> Tuple[float, float]:
    w, d = field_size()
    x = col * P.PITCH - w * 0.5
    y = row * P.PITCH - d * 0.5
    return x, y


def normalized(x: float, y: float) -> Tuple[float, float]:
    w, d = field_size()
    return (x + w * 0.5) / max(w, 1e-6), (y + d * 0.5) / max(d, 1e-6)


def height_factor(x: float, y: float) -> float:
    nx, ny = normalized(x, y)
    land = _land_sdf(nx, ny)
    inside = smoothstep((-land) / 0.18)

    h = 0.58
    h += 0.18 * math.sin(nx * 2.7 + ny * 1.9)
    h += 0.12 * math.sin(nx * 8.1 - ny * 5.4 + 0.6)
    h += 0.07 * math.sin(nx * 16.0 + ny * 11.0)
    h = h * (0.45 + 0.55 * inside)
    h += 0.28 * inside

    river = _river(nx, ny)
    h *= 1.0 - 0.72 * river

    fade = 1.0 - smoothstep((nx - 0.36) / 0.42)
    h *= fade
    if h < 0.0:
        return 0.0
    if h > 1.0:
        return 1.0
    return h


def tube_present(col: int, row: int) -> bool:
    x, y = tube_origin(col, row)
    nx, ny = normalized(x, y)
    h = height_factor(x, y)
    land = _land_sdf(nx, ny)
    river = _river(nx, ny)

    density = 0.12 + 0.88 * smoothstep((-land) / 0.12)
    density *= 1.0 - 0.94 * river
    density *= 1.0 - smoothstep((nx - 0.38) / 0.48)
    # scatter a few outliers into the fade
    density = max(density, 0.16 * (1.0 - smoothstep((nx - 0.30) / 0.50)) * (1.0 if h > 0.04 else 0.0))

    n = _hash01(col + 17, row + 91)
    if h < 0.035 and n > 0.18:
        return False
    return n < density * 0.97 + 0.02


def tube_height(col: int, row: int) -> float:
    x, y = tube_origin(col, row)
    h = height_factor(x, y)
    jitter = 0.82 + 0.18 * _hash01(col, row)
    z = P.MAX_HEIGHT * h * jitter
    if z < P.MIN_HEIGHT:
        return P.DOT_HEIGHT if h > 0.02 else 0.0
    return z


def iter_tubes() -> Iterator[Tuple[float, float, float, bool]]:
    """Yield (x, y, height, is_dot) for every tube that should be placed."""
    for row in range(P.ROWS):
        for col in range(P.COLS):
            if not tube_present(col, row):
                continue
            z = tube_height(col, row)
            if z <= 0.05:
                continue
            x, y = tube_origin(col, row)
            yield x, y, z, z <= P.DOT_HEIGHT + 0.05


def wave_axis(x: float, y: float) -> float:
    """Coordinate along the wave ridges (mostly Y, slight X slant)."""
    return y + P.WAVE_SLANT * x


def wave_z(x: float, y: float) -> float:
    w, d = field_size()
    nx = (x + w * 0.5) / max(w, 1e-6)
    u = wave_axis(x, y)
    period = d / max(P.WAVE_PERIODS, 0.1)
    z = P.WAVE_AMP * math.sin(2.0 * math.pi * u / period)
    z += P.WAVE_AMP * 0.18 * math.sin(2.0 * math.pi * u / (period * 2.3) + 0.5)
    z += P.WAVE_AMP * 0.06 * math.sin(2.0 * math.pi * x / (w * 0.7) + 0.3)
    amp = 0.20 + 0.80 * smoothstep((nx - P.WAVE_X_START + 0.12) / 0.32)
    return z * amp + P.WAVE_AMP * 0.45 * amp


def wave_normal(x: float, y: float) -> Tuple[float, float, float]:
    e = 3.0
    dx = wave_z(x + e, y) - wave_z(x - e, y)
    dy = wave_z(x, y + e) - wave_z(x, y - e)
    nx, ny, nz = -dx / (2 * e), -dy / (2 * e), 1.0
    mag = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / mag, ny / mag, nz / mag


def wave_shade_rgb(x: float, y: float) -> Tuple[int, int, int]:
    nx, ny, nz = wave_normal(x, y)
    lx, ly, lz = 0.35, 0.15, 0.92
    lm = math.sqrt(lx * lx + ly * ly + lz * lz)
    ndotl = max(0.0, (nx * lx + ny * ly + nz * lz) / lm)
    spec = ndotl ** 7
    t = 0.06 + 0.72 * ndotl + 0.22 * spec
    if t < 0.45:
        u = t / 0.45
        c = int(12 + 40 * u)
        return (c, c, c + 2)
    u = (t - 0.45) / 0.55
    c = int(48 + 200 * (u ** 0.85))
    return (min(c, 250), min(c, 250), min(c + 4, 252))


def wave_bounds() -> Tuple[float, float, float, float]:
    w, d = field_size()
    x0 = -w * 0.5 + w * P.WAVE_X_START
    x1 = w * 0.5 + P.WAVE_OVERHANG
    y0 = -d * 0.5 - 40.0
    y1 = d * 0.5 + 40.0
    return x0, x1, y0, y1


def wave_points(nu: int | None = None, nv: int | None = None) -> List[List[Point3]]:
    nu = P.WAVE_NU if nu is None else nu
    nv = P.WAVE_NV if nv is None else nv
    x0, x1, y0, y1 = wave_bounds()
    grid: List[List[Point3]] = []
    for i in range(nu):
        col: List[Point3] = []
        tx = i / float(nu - 1)
        x = x0 + (x1 - x0) * tx
        for j in range(nv):
            ty = j / float(nv - 1)
            y = y0 + (y1 - y0) * ty
            col.append((x, y, wave_z(x, y)))
        grid.append(col)
    return grid
