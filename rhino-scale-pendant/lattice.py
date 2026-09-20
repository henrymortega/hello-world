"""Lattice layout helpers shared by the preview, 3dm writer, and Rhino script."""

from __future__ import annotations

import math
from typing import Iterable, List, Tuple

import params as P

Point = Tuple[float, float]


def smoothstep(t: float) -> float:
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    return t * t * (3.0 - 2.0 * t)


def fade_scale(y: float) -> float:
    """1 at the top of the pendant, 0 in the solid bottom band."""
    t = (y + P.HEIGHT * 0.5) / P.HEIGHT
    if t >= P.FADE_END:
        return 1.0
    if t <= P.FADE_START:
        return 0.0
    return smoothstep((t - P.FADE_START) / (P.FADE_END - P.FADE_START))


def cell_centers() -> List[Point]:
    total_w = (P.COLS - 1) * P.COL_PITCH
    y0 = P.HEIGHT * 0.5 - P.TOP_MARGIN
    centers: List[Point] = []
    for row in range(P.ROWS):
        y = y0 - row * P.ROW_PITCH
        if y < -P.HEIGHT * 0.5 + 8.0:
            break
        xoff = 0.5 * P.COL_PITCH if row % 2 else 0.0
        n = P.COLS + (1 if row % 2 else 0)
        x0 = -total_w * 0.5 - xoff
        for col in range(n):
            centers.append((x0 + col * P.COL_PITCH, y))
    return centers


def superellipse_points(cx: float, cy: float, rx: float, ry: float, n: float, count: int = 64) -> List[Point]:
    """Closed polyline samples of a superellipse (|x/rx|^n + |y/ry|^n = 1)."""
    pts: List[Point] = []
    for i in range(count):
        a = 2.0 * math.pi * i / count
        # Superellipse parametrization via signed powers
        ca = math.cos(a)
        sa = math.sin(a)
        x = rx * math.copysign(abs(ca) ** (2.0 / n), ca)
        y = ry * math.copysign(abs(sa) ** (2.0 / n), sa)
        pts.append((cx + x, cy + y))
    return pts


def iter_holes(min_scale: float = 0.08) -> Iterable[tuple[float, float, float, float, float]]:
    """Yield (cx, cy, rx, ry, scale) for every hole that should be cut or pocketed."""
    for cx, cy in cell_centers():
        scale = fade_scale(cy)
        if scale < min_scale:
            continue
        yield cx, cy, 0.5 * P.CELL_W * scale, 0.5 * P.CELL_H * scale, scale
