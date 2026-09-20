"""Simple top/perspective preview of the robot vacuum."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

import params as P

OUT = Path(__file__).resolve().parent / "preview.png"


def proj(x, y, z):
    sx = 0.9 * x + 0.35 * y
    sy = -0.25 * x + 0.55 * y - 0.85 * z
    return sx, sy


def to_px(pts, bounds, size, pad=0.12):
    minx, miny, maxx, maxy = bounds
    out = []
    for sx, sy in pts:
        px = int((sx - minx) / (maxx - minx) * (1 - 2 * pad) * size + pad * size)
        py = int((sy - miny) / (maxy - miny) * (1 - 2 * pad) * size + pad * size)
        out.append((px, py))
    return out


def ellipse(x, y, z, rx, ry, n=48):
    return [proj(x + rx * math.cos(a), y + ry * math.sin(a), z) for a in [2 * math.pi * i / n for i in range(n)]]


def render(size=1000):
    samples = []
    for z, r in ((0, P.BODY_R), (P.BODY_Z0 + P.BODY_H, P.BODY_R), (P.LIDAR_Z + P.LIDAR_H, P.LIDAR_R)):
        samples.extend(ellipse(0, 0, z, r, r))
    samples.append(proj(P.BUTTON_X, 0, P.BUTTON_Z + 3))
    samples.append(proj(0, -P.BODY_R - 30, 0))
    xs = [p[0] for p in samples]
    ys = [p[1] for p in samples]
    bounds = (min(xs), min(ys), max(xs), max(ys))

    img = Image.new("RGB", (size, size), (220, 222, 226))
    draw = ImageDraw.Draw(img)

    # floor shadow
    shadow = ellipse(8, -8, 0, P.BODY_R * 0.95, P.BODY_R * 0.78)
    draw.polygon(to_px(shadow, bounds, size), fill=(200, 202, 206))

    # body side strip
    z0, z1 = P.BODY_Z0, P.BODY_Z0 + P.BODY_H
    for i in range(36):
        a0 = 2 * math.pi * i / 36
        a1 = 2 * math.pi * (i + 1) / 36
        lit = 0.75 + 0.25 * math.cos(a0 - 0.8)
        col = tuple(int(c * lit) for c in P.WHITE[:3])
        quad = [
            proj(P.BODY_R * math.cos(a0), P.BODY_R * math.sin(a0), z0),
            proj(P.BODY_R * math.cos(a1), P.BODY_R * math.sin(a1), z0),
            proj(P.BODY_R * math.cos(a1), P.BODY_R * math.sin(a1), z1),
            proj(P.BODY_R * math.cos(a0), P.BODY_R * math.sin(a0), z1),
        ]
        draw.polygon(to_px(quad, bounds, size), fill=col)

    # bumper front
    for i in range(18):
        t0, t1 = i / 18, (i + 1) / 18
        a0 = math.radians(-95 + 190 * t0)
        a1 = math.radians(-95 + 190 * t1)
        r = P.BUMPER_R
        quad = [
            proj(r * math.cos(a0), r * math.sin(a0), P.BUMPER_Z),
            proj(r * math.cos(a1), r * math.sin(a1), P.BUMPER_Z),
            proj(r * math.cos(a1), r * math.sin(a1), P.BUMPER_Z + P.BUMPER_H),
            proj(r * math.cos(a0), r * math.sin(a0), P.BUMPER_Z + P.BUMPER_H),
        ]
        draw.polygon(to_px(quad, bounds, size), fill=P.CHARCOAL[:3])

    # top disc
    top = ellipse(0, 0, z1 + P.TOP_DOME_H, P.BODY_R * 0.98, P.BODY_R * 0.98)
    draw.polygon(to_px(top, bounds, size), fill=P.WHITE[:3], outline=(210, 212, 216))

    # lidar
    lid = ellipse(0, 0, P.LIDAR_Z + P.LIDAR_H, P.LIDAR_R, P.LIDAR_R)
    draw.polygon(to_px(lid, bounds, size), fill=P.DARK[:3])
    win = ellipse(0, 0, P.LIDAR_Z + 10, P.LIDAR_WINDOW_R, P.LIDAR_WINDOW_R)
    draw.polygon(to_px(win, bounds, size), outline=P.SMOKE[:3])

    # button + LED
    btn = ellipse(P.BUTTON_X, 0, P.BUTTON_Z + 2, P.BUTTON_R, P.BUTTON_R)
    led = ellipse(P.BUTTON_X, 0, P.BUTTON_Z + 2.2, P.LED_R_OUT, P.LED_R_OUT)
    draw.polygon(to_px(led, bounds, size), outline=P.ACCENT[:3])
    draw.polygon(to_px(btn, bounds, size), fill=P.DARK[:3])

    # wheels (visible as ellipses on sides)
    for wx in (-P.WHEEL_X, P.WHEEL_X):
        wh = ellipse(wx, 0, P.WHEEL_Z, 6, P.WHEEL_R)
        draw.polygon(to_px(wh, bounds, size), fill=P.RUBBER[:3])

    return img


if __name__ == "__main__":
    render().save(OUT)
    print("wrote", OUT)
