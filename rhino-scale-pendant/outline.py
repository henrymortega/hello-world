"""Rounded-rectangle outline samples."""

from __future__ import annotations

import math
from typing import List, Tuple

Point = Tuple[float, float]


def rounded_rect_points(w: float, h: float, r: float, n_arc: int = 10) -> List[Point]:
    hw, hh = w * 0.5, h * 0.5
    r = min(r, hw - 0.1, hh - 0.1)
    corners = (
        (hw - r, hh - r, 0.0, 90.0),
        (-hw + r, hh - r, 90.0, 180.0),
        (-hw + r, -hh + r, 180.0, 270.0),
        (hw - r, -hh + r, 270.0, 360.0),
    )
    pts: List[Point] = []
    for cx, cy, a0, a1 in corners:
        for i in range(n_arc + 1):
            if pts and i == 0:
                continue
            a = math.radians(a0 + (a1 - a0) * i / n_arc)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts
