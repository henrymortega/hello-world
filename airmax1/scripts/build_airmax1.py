#!/usr/bin/env python3
"""
Realistic Nike Air Max 1 (US 9 Left) — componentized Rhino .3dm for V-Ray.

Built from:
  - Nike PDP / SNS FZ5808-102 multi-angle product photography
  - Nike DNA archive mudguard notes (7 mm mid / 15–17 mm heel)
  - Lab stack & width figures for men's scale

Approach: thin panel shells on an accurate last (not solid sausage lofts),
sculpted midsole with visible Max Air capsule, waffle outsole.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import rhino3dm as r3d

from geometry_utils import (
    box_mesh,
    curve_from_pts,
    cylinder_mesh,
    loft_mesh,
    pipe_along_polyline,
    pt,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "Nike_AirMax1_US9_Left.3dm"

# ---------------------------------------------------------------------------
# Spec (US 9)
# ---------------------------------------------------------------------------
L = 295.0  # external length mm
HEEL_STACK = 32.2
FF_STACK = 20.1
OUTSOLE_T = 5.5
HEEL_W = 81.8
FF_W = 107.9


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


# ---------------------------------------------------------------------------
# Hand-tuned profiles from Nike FZ5808-102 lateral (heel=0 → toe=L)
# Values are absolute Z from ground, or heights — matched to photo + lab.
# ---------------------------------------------------------------------------

def outsole_bottom_z(x):
    """Ground contact with toe spring & slight heel lift."""
    t = x / L
    z = 0.0
    if t > 0.82:
        z = 3.5 * smoothstep((t - 0.82) / 0.18)  # toe spring
    if t < 0.06:
        z = 1.2 * (1 - t / 0.06)  # heel bevel
    return z


def outsole_top_z(x):
    return outsole_bottom_z(x) + OUTSOLE_T


def midsole_top_z(x):
    """Top of midsole / bottom of upper — lab drop profile."""
    t = x / L
    z = lerp(HEEL_STACK, FF_STACK, smoothstep(min(1.0, t / 0.88)))
    if t > 0.90:
        z += 2.0 * smoothstep((t - 0.90) / 0.10)
    return z + outsole_bottom_z(x) * 0.15


def mudguard_top_z(x):
    """Black mudguard crest — Nike DNA wave (7 mid / 15–17 heel)."""
    t = x / L
    base = midsole_top_z(x)
    if t < 0.10:
        h = lerp(17.0, 15.0, t / 0.10)
    elif t < 0.32:
        h = lerp(15.0, 7.0, smoothstep((t - 0.10) / 0.22))
    elif t < 0.52:
        h = 7.0
    elif t < 0.72:
        h = lerp(7.0, 14.0, smoothstep((t - 0.52) / 0.20))
    elif t < 0.88:
        h = lerp(14.0, 20.0, smoothstep((t - 0.72) / 0.16))
    else:
        h = lerp(20.0, 16.0, (t - 0.88) / 0.12)
    return base + h


def collar_top_z(x):
    """Padded collar / upper topline (excludes tongue). Matched to FZ5808-102 lateral."""
    t = x / L
    # Heel collar ~78 mm, slopes down through eyestay, then toebox ~48–55 mm
    if t < 0.04:
        return lerp(52.0, 78.0, t / 0.04)
    if t < 0.18:
        return lerp(78.0, 74.0, (t - 0.04) / 0.14)
    if t < 0.36:
        return lerp(74.0, 62.0, smoothstep((t - 0.18) / 0.18))
    if t < 0.55:
        return lerp(62.0, 56.0, (t - 0.36) / 0.19)
    if t < 0.72:
        return lerp(56.0, 52.0, smoothstep((t - 0.55) / 0.17))
    if t < 0.88:
        return lerp(52.0, 40.0, smoothstep((t - 0.72) / 0.16))
    return lerp(40.0, 24.0, smoothstep((t - 0.88) / 0.12))


def tongue_top_z(x):
    """Tongue peak — dominant mid silhouette on product photos (~110 mm)."""
    t = x / L
    base = collar_top_z(x)
    if t < 0.28 or t > 0.82:
        return base
    u = (t - 0.28) / 0.54
    # Smooth hump
    peak = 110.0 * (math.sin(math.pi * u) ** 1.05)
    return max(base, peak)


def last_section_upper(x, inset=0.0, count=48):
    """Closed upper last slice at X — rounded footwear section above midsole."""
    z0 = midsole_top_z(x) + 0.2
    z1 = collar_top_z(x)
    hw0 = sole_half_width(x) * 0.90 - inset
    pts = []
    for i in range(count):
        a = 2 * math.pi * i / count
        # Param: 0 at bottom center going around
        # Use elliptical last with flat-ish sole and rounded vamp
        sy = math.sin(a)
        cz = math.cos(a)  # +1 top, -1 bottom
        if cz < 0:
            # sole plate of upper (bottom)
            y = hw0 * sy
            z = z0 + 1.2 * (1 - abs(sy))  # slight camber
        else:
            # upper — taper width toward topline
            u = cz  # 0 at mid sides → 1 at top
            hw = hw0 * lerp(1.0, 0.70, u ** 1.15)
            y = hw * sy
            z = z0 + (z1 - z0) * (u ** 0.75)
        pts.append(pt(x, y, z))
    return pts


def thin_last_shell(xs, thickness=2.0, count=48):
    outer = [last_section_upper(x, 0.0, count) for x in xs]
    inner = [last_section_upper(x, thickness, count) for x in xs]
    # Build solid thin wall by lofting mid section (visual shell)
    mid = []
    for o, i in zip(outer, inner):
        mid.append(
            [
                pt(0.5 * (a.X + b.X), 0.5 * (a.Y + b.Y), 0.5 * (a.Z + b.Z))
                for a, b in zip(o, i)
            ]
        )
    return loft_mesh(outer, True)


def sole_half_width(x):
    t = x / L
    if t < 0.15:
        return lerp(HEEL_W * 0.48, HEEL_W * 0.50, t / 0.15)
    if t < 0.42:
        return lerp(HEEL_W * 0.50, FF_W * 0.47, smoothstep((t - 0.15) / 0.27))
    if t < 0.72:
        return lerp(FF_W * 0.47, FF_W * 0.50, smoothstep((t - 0.42) / 0.30))
    if t < 0.90:
        return lerp(FF_W * 0.50, 38.0, smoothstep((t - 0.72) / 0.18))
    return lerp(38.0, 18.0, smoothstep((t - 0.90) / 0.10))


def upper_half_width(x, z):
    """Last width at height z — tapers toward topline."""
    hw0 = sole_half_width(x) * 0.92
    z0 = midsole_top_z(x)
    z1 = collar_top_z(x)
    if z1 <= z0:
        return hw0 * 0.85
    u = clamp((z - z0) / (z1 - z0), 0, 1)
    # AM1 last: relatively parallel sides then taper to collar
    return hw0 * lerp(1.0, 0.72, u ** 1.1)


# Air window (from photo + lab)
AIR = dict(cx=42.0, cz=16.8, length=47.0, height=17.2, depth_scale=0.88)


# ---------------------------------------------------------------------------
# Mesh primitives for panels
# ---------------------------------------------------------------------------

def grid_shell(xs, z0_fn, z1_fn, y_sign, n_z=10, thickness=1.6, width_fn=None):
    """Open panel on lateral (y_sign=+1) or medial (-1) side as a thin shell."""
    if width_fn is None:
        width_fn = upper_half_width
    outer = []
    inner = []
    for x in xs:
        row_o = []
        row_i = []
        z0 = z0_fn(x)
        z1 = z1_fn(x)
        if z1 <= z0 + 1.0:
            z1 = z0 + 1.5
        for j in range(n_z):
            u = j / (n_z - 1)
            z = lerp(z0, z1, u)
            hw = width_fn(x, z)
            y = y_sign * hw
            row_o.append(pt(x, y, z))
            row_i.append(pt(x, y - y_sign * thickness, z))
        outer.append(row_o)
        inner.append(row_i)
    # Build mesh from outer grid + thickness bridge
    mesh = r3d.Mesh()
    # vertices: outer then inner
    rows = len(xs)
    cols = n_z
    for row in outer:
        for p in row:
            mesh.Vertices.Add(p.X, p.Y, p.Z)
    for row in inner:
        for p in row:
            mesh.Vertices.Add(p.X, p.Y, p.Z)

    def vid(side, r, c):  # side 0 outer 1 inner
        return side * rows * cols + r * cols + c

    for r in range(rows - 1):
        for c in range(cols - 1):
            # outer
            mesh.Faces.AddFace(vid(0, r, c), vid(0, r, c + 1), vid(0, r + 1, c + 1), vid(0, r + 1, c))
            # inner (reversed)
            mesh.Faces.AddFace(vid(1, r, c), vid(1, r + 1, c), vid(1, r + 1, c + 1), vid(1, r, c + 1))
    # edges
    for r in range(rows - 1):
        mesh.Faces.AddFace(vid(0, r, 0), vid(0, r + 1, 0), vid(1, r + 1, 0), vid(1, r, 0))
        mesh.Faces.AddFace(
            vid(0, r, cols - 1), vid(1, r, cols - 1), vid(1, r + 1, cols - 1), vid(0, r + 1, cols - 1)
        )
    for c in range(cols - 1):
        mesh.Faces.AddFace(vid(0, 0, c), vid(1, 0, c), vid(1, 0, c + 1), vid(0, 0, c + 1))
        mesh.Faces.AddFace(
            vid(0, rows - 1, c),
            vid(0, rows - 1, c + 1),
            vid(1, rows - 1, c + 1),
            vid(1, rows - 1, c),
        )
    mesh.Normals.ComputeNormals()
    mesh.Compact()
    return mesh


def vamp_top_shell(xs, n_y=12, thickness=1.8):
    """Instep / toebox top panel across Y."""
    rows = []
    for x in xs:
        z0 = midsole_top_z(x) + 1.0
        z1 = min(tongue_top_z(x), collar_top_z(x) + 8)
        # crown height at centerline
        hw = upper_half_width(x, (z0 + z1) * 0.5)
        row = []
        for j in range(n_y):
            v = j / (n_y - 1)
            y = lerp(-hw, hw, v)
            # elliptical crown
            crown = math.sin(math.pi * v)
            z = lerp(z0 + 2, z1, 0.35 + 0.65 * crown)
            # near edges stay lower (mudguard meet)
            edge = min(v, 1 - v) * 2
            z = lerp(mudguard_top_z(x) + 1.0, z, smoothstep(edge))
            row.append(pt(x, y, z))
        rows.append(row)
    # thicken downward
    rows_i = []
    for row in rows:
        rows_i.append([pt(p.X, p.Y, p.Z - thickness) for p in row])
    return loft_pair(rows, rows_i)


def loft_pair(outer_rows, inner_rows):
    mesh = r3d.Mesh()
    rows = len(outer_rows)
    cols = len(outer_rows[0])
    for row in outer_rows:
        for p in row:
            mesh.Vertices.Add(p.X, p.Y, p.Z)
    for row in inner_rows:
        for p in row:
            mesh.Vertices.Add(p.X, p.Y, p.Z)

    def vid(side, r, c):
        return side * rows * cols + r * cols + c

    for r in range(rows - 1):
        for c in range(cols - 1):
            mesh.Faces.AddFace(vid(0, r, c), vid(0, r, c + 1), vid(0, r + 1, c + 1), vid(0, r + 1, c))
            mesh.Faces.AddFace(vid(1, r, c), vid(1, r + 1, c), vid(1, r + 1, c + 1), vid(1, r, c + 1))
    for r in range(rows - 1):
        mesh.Faces.AddFace(vid(0, r, 0), vid(0, r + 1, 0), vid(1, r + 1, 0), vid(1, r, 0))
        mesh.Faces.AddFace(
            vid(0, r, cols - 1), vid(1, r, cols - 1), vid(1, r + 1, cols - 1), vid(0, r + 1, cols - 1)
        )
    for c in range(cols - 1):
        mesh.Faces.AddFace(vid(0, 0, c), vid(1, 0, c), vid(1, 0, c + 1), vid(0, 0, c + 1))
        mesh.Faces.AddFace(
            vid(0, rows - 1, c),
            vid(0, rows - 1, c + 1),
            vid(1, rows - 1, c + 1),
            vid(1, rows - 1, c),
        )
    mesh.Normals.ComputeNormals()
    mesh.Compact()
    return mesh


def solid_loft_along_x(xs, section_fn):
    return loft_mesh([section_fn(x) for x in xs], cap=True)


def oval_section(x, half_w, z0, z1, count=36, squat=0.55):
    """Vertical oval / rounded section in YZ."""
    pts = []
    h = max(1.0, z1 - z0)
    cz = 0.5 * (z0 + z1)
    for i in range(count):
        a = 2 * math.pi * i / count
        cy = math.sin(a)
        czn = math.cos(a)
        y = half_w * cy
        exp = squat if czn < 0 else 0.85
        z = cz + (h * 0.5) * math.copysign(abs(czn) ** exp, czn)
        pts.append(pt(x, y, z))
    return pts


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

class Doc:
    def __init__(self):
        self.doc = r3d.File3dm()
        self.doc.Settings.ModelUnitSystem = r3d.UnitSystem.Millimeters
        self.doc.Settings.ModelAbsoluteTolerance = 0.01
        self.doc.ApplicationName = "AirMax1 Realistic Builder"
        self.doc.StartSectionComments = (
            "Nike Air Max 1 US9 Left — realistic componentized model for V-Ray. "
            "Profiles from Nike FZ5808-102 product photography + DNA/lab dimensions."
        )
        self.layers = {}
        self.mats = {}
        self.groups = {}

    def layer(self, name, rgb, parent=None):
        if name in self.layers:
            return
        layer = r3d.Layer()
        layer.Name = name
        layer.Color = (*rgb, 255)
        if parent:
            layer.ParentLayerId = self.doc.Layers[self.layers[parent]].Id
        self.layers[name] = self.doc.Layers.Add(layer)

    def material(self, name, rgb, **kw):
        if name in self.mats:
            return
        m = r3d.Material()
        m.Name = name
        m.DiffuseColor = (*rgb, 255)
        m.Transparency = kw.get("transparency", 0.0)
        m.Shine = kw.get("shine", 0.3) * 255
        m.Reflectivity = kw.get("reflectivity", 0.05)
        m.IndexOfRefraction = kw.get("ior", 1.5)
        hint = kw.get("notes", "")
        if hint:
            m.SetUserString("VRayHint", hint)
            m.SetUserString("Roughness", str(kw.get("roughness", 0.5)))
        try:
            m.ToPhysicallyBased()
            p = m.PhysicallyBased
            if p:
                p.Roughness = kw.get("roughness", 0.5)
                p.Metallic = kw.get("metallic", 0.0)
                p.Opacity = 1.0 - kw.get("transparency", 0.0)
                if kw.get("transparency", 0) > 0.2:
                    p.OpacityIOR = kw.get("ior", 1.49)
        except Exception:
            pass
        self.mats[name] = self.doc.Materials.Add(m)

    def group(self, name):
        if name in self.groups:
            return
        g = r3d.Group()
        g.Name = name
        self.doc.Groups.Add(g)
        self.groups[name] = self.doc.Groups.FindName(name).Index

    def add(self, geo, name, layer, mat, group=None, user=None):
        a = r3d.ObjectAttributes()
        a.Name = name
        a.LayerIndex = self.layers[layer]
        a.MaterialIndex = self.mats[mat]
        a.MaterialSource = r3d.ObjectMaterialSource.MaterialFromObject
        if group:
            a.AddToGroup(self.groups[group])
        if user:
            for k, v in user.items():
                a.SetUserString(k, str(v))
        self.doc.Objects.Add(geo, a)

    def add_curve(self, crv, name, layer):
        a = r3d.ObjectAttributes()
        a.Name = name
        a.LayerIndex = self.layers[layer]
        self.doc.Objects.AddCurve(crv, a)

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        assert self.doc.Write(str(path), 8)


def setup(d: Doc):
    parents = [
        ("00_Reference", (120, 120, 120)),
        ("01_Sole", (30, 30, 30)),
        ("02_Midsole", (240, 240, 240)),
        ("03_AirUnit", (180, 220, 255)),
        ("04_Upper", (245, 245, 245)),
        ("05_Overlays", (180, 175, 165)),
        ("06_Hardware", (20, 20, 20)),
        ("07_SoftGoods", (250, 250, 250)),
    ]
    for n, c in parents:
        d.layer(n, c)
    kids = [
        ("00_Reference::Profiles", "00_Reference", (80, 80, 255)),
        ("01_Sole::Outsole", "01_Sole", (15, 15, 15)),
        ("01_Sole::Waffle", "01_Sole", (25, 25, 25)),
        ("01_Sole::ToeHeelWrap", "01_Sole", (160, 20, 30)),
        ("02_Midsole::Body", "02_Midsole", (245, 245, 245)),
        ("03_AirUnit::Window", "03_AirUnit", (200, 230, 250)),
        ("03_AirUnit::Pillars", "03_AirUnit", (190, 210, 230)),
        ("03_AirUnit::Membrane", "03_AirUnit", (210, 225, 240)),
        ("04_Upper::MeshBase", "04_Upper", (250, 250, 250)),
        ("04_Upper::Collar", "04_Upper", (240, 240, 240)),
        ("04_Upper::Lining", "04_Upper", (20, 20, 20)),
        ("05_Overlays::Mudguard", "05_Overlays", (20, 20, 20)),
        ("05_Overlays::SuedeQuarter", "05_Overlays", (210, 205, 195)),
        ("05_Overlays::HeelCounter", "05_Overlays", (205, 200, 190)),
        ("05_Overlays::Swoosh", "05_Overlays", (10, 10, 10)),
        ("05_Overlays::Eyestay", "05_Overlays", (215, 210, 200)),
        ("06_Hardware::Eyelets", "06_Hardware", (30, 30, 30)),
        ("06_Hardware::LaceLock", "06_Hardware", (15, 15, 15)),
        ("07_SoftGoods::Tongue", "07_SoftGoods", (250, 250, 250)),
        ("07_SoftGoods::Laces", "07_SoftGoods", (245, 245, 245)),
        ("07_SoftGoods::Insole", "07_SoftGoods", (235, 232, 225)),
        ("07_SoftGoods::TongueLabel", "07_SoftGoods", (255, 255, 255)),
    ]
    for n, p, c in kids:
        d.layer(n, c, p)

    mats = [
        ("MAT_Rubber", (22, 22, 22), dict(roughness=0.7, shine=0.2, notes="Black rubber outsole")),
        ("MAT_Rubber_Red", (170, 30, 35), dict(roughness=0.55, shine=0.3, notes="OG accent wrap")),
        ("MAT_Foam", (248, 248, 245), dict(roughness=0.8, shine=0.12, notes="White phylon midsole")),
        ("MAT_AirClear", (200, 225, 240), dict(transparency=0.78, ior=1.49, roughness=0.04, shine=0.9, reflectivity=0.12, notes="Clear TPU Max Air window")),
        ("MAT_AirMem", (195, 210, 225), dict(transparency=0.4, ior=1.4, roughness=0.2, shine=0.4, notes="Air bag membrane")),
        ("MAT_AirPillar", (180, 195, 210), dict(transparency=0.3, roughness=0.15, shine=0.5, notes="Air unit ribs")),
        ("MAT_Mesh", (250, 250, 248), dict(roughness=0.85, shine=0.08, notes="Engineered mesh — add weave opacity/bump")),
        ("MAT_Suede", (206, 200, 188), dict(roughness=0.92, shine=0.04, notes="Bone/grey suede overlays")),
        ("MAT_LeatherBlk", (18, 18, 18), dict(roughness=0.42, shine=0.38, notes="Synthetic leather mudguard/swoosh")),
        ("MAT_Collar", (245, 245, 243), dict(roughness=0.8, shine=0.08, notes="Padded collar mesh")),
        ("MAT_Lining", (25, 25, 25), dict(roughness=0.75, shine=0.1, notes="Black interior lining")),
        ("MAT_Plastic", (25, 25, 25), dict(roughness=0.28, shine=0.55, metallic=0.04, notes="Lace lock / eyelets")),
        ("MAT_Lace", (245, 245, 243), dict(roughness=0.7, shine=0.12, notes="Flat lace")),
        ("MAT_Label", (255, 255, 255), dict(roughness=0.45, shine=0.25, notes="Tongue woven label")),
        ("MAT_Insole", (236, 232, 224), dict(roughness=0.8, shine=0.1, notes="Sockliner")),
    ]
    for n, rgb, kw in mats:
        d.material(n, rgb, **kw)
    for g in ["GRP_Sole", "GRP_Midsole", "GRP_Air", "GRP_Upper", "GRP_Overlays", "GRP_Hardware", "GRP_Soft"]:
        d.group(g)


# ---------------------------------------------------------------------------
# Build components
# ---------------------------------------------------------------------------

def build_profiles(d: Doc):
    xs = list(np.linspace(0, L, 60))
    curves = [
        ("Profile_OutsoleBottom", [pt(x, 0, outsole_bottom_z(x)) for x in xs]),
        ("Profile_OutsoleTop", [pt(x, 0, outsole_top_z(x)) for x in xs]),
        ("Profile_MidsoleTop", [pt(x, 0, midsole_top_z(x)) for x in xs]),
        ("Profile_MudguardCrest", [pt(x, sole_half_width(x), mudguard_top_z(x)) for x in xs]),
        ("Profile_Collar", [pt(x, 0, collar_top_z(x)) for x in xs]),
        ("Profile_SilhouetteTop", [pt(x, 0, tongue_top_z(x)) for x in xs]),
    ]
    for name, pts in curves:
        d.add_curve(curve_from_pts(pts, 3), name, "00_Reference::Profiles")


def build_outsole(d: Doc):
    xs = list(np.linspace(0, L, 36))

    def sec(x):
        return oval_section(x, sole_half_width(x) * 0.98, outsole_bottom_z(x), outsole_top_z(x), 40, squat=0.35)

    d.add(
        solid_loft_along_x(xs, sec),
        "Outsole_Base",
        "01_Sole::Outsole",
        "MAT_Rubber",
        "GRP_Sole",
    )

    # Waffle lugs — AM1 style square grid forefoot + heel pods
    for ix in range(7):
        for iy in range(-4, 5):
            x = 145 + ix * 13.5
            y = iy * 10.5
            if abs(y) > sole_half_width(x) - 9:
                continue
            z0 = outsole_bottom_z(x) - 0.2
            d.add(
                box_mesh(x - 3.4, y - 3.4, z0 - 2.6, x + 3.4, y + 3.4, z0 + 0.4),
                f"Waffle_FF_{ix}_{iy}",
                "01_Sole::Waffle",
                "MAT_Rubber",
                "GRP_Sole",
            )
    for ix in range(3):
        for iy in range(-2, 3):
            x = 16 + ix * 15
            y = iy * 11
            if abs(y) > sole_half_width(x) - 7:
                continue
            z0 = outsole_bottom_z(x) - 0.2
            d.add(
                box_mesh(x - 5.5, y - 5.0, z0 - 2.8, x + 5.5, y + 5.0, z0 + 0.3),
                f"Waffle_Heel_{ix}_{iy}",
                "01_Sole::Waffle",
                "MAT_Rubber",
                "GRP_Sole",
            )

    # Toe / heel wraps (heritage)
    toe_xs = list(np.linspace(L - 42, L - 2, 12))
    d.add(
        solid_loft_along_x(
            toe_xs,
            lambda x: oval_section(
                x, sole_half_width(x) * 1.01, outsole_bottom_z(x), outsole_top_z(x) + 3.0, 36, 0.3
            ),
        ),
        "Outsole_ToeWrap",
        "01_Sole::ToeHeelWrap",
        "MAT_Rubber_Red",
        "GRP_Sole",
    )
    heel_xs = list(np.linspace(1, 38, 12))
    d.add(
        solid_loft_along_x(
            heel_xs,
            lambda x: oval_section(
                x, sole_half_width(x) * 1.01, outsole_bottom_z(x), outsole_top_z(x) + 2.2, 36, 0.3
            ),
        ),
        "Outsole_HeelWrap",
        "01_Sole::ToeHeelWrap",
        "MAT_Rubber_Red",
        "GRP_Sole",
    )


def build_midsole(d: Doc):
    xs = list(np.linspace(0, L, 44))

    def sec(x):
        # Slight waist in midfoot; fuller heel & forefoot — AM1 read
        t = x / L
        waist = 1.0 - 0.04 * math.sin(math.pi * clamp((t - 0.15) / 0.55, 0, 1))
        return oval_section(
            x,
            sole_half_width(x) * 0.995 * waist,
            outsole_top_z(x) - 0.3,
            midsole_top_z(x),
            48,
            squat=0.42,
        )

    d.add(
        solid_loft_along_x(xs, sec),
        "Midsole_Foam",
        "02_Midsole::Body",
        "MAT_Foam",
        "GRP_Midsole",
        user={"HeelStack_mm": HEEL_STACK, "ForefootStack_mm": FF_STACK},
    )

    # Flex grooves (visual AM1 midsole notches near ball)
    for x in (195.0, 210.0):
        hw = sole_half_width(x) * 0.99
        z0 = outsole_top_z(x) + 2
        z1 = midsole_top_z(x) - 1
        d.add(
            box_mesh(x - 1.2, -hw - 0.5, z0, x + 1.2, hw + 0.5, z1),
            f"Midsole_FlexGroove_{int(x)}",
            "02_Midsole::Body",
            "MAT_Foam",
            "GRP_Midsole",
        )


def build_air_unit(d: Doc):
    cx, cz = AIR["cx"], AIR["cz"]
    hl, hh = AIR["length"] * 0.5, AIR["height"] * 0.5
    hw = sole_half_width(cx) * AIR["depth_scale"]

    # Capsule window through midsole (clear shell)
    secs = []
    for i in range(16):
        t = i / 15
        x = cx - hl + AIR["length"] * t
        # rounded ends
        if t < 0.12:
            s = math.sin((t / 0.12) * math.pi / 2)
        elif t > 0.88:
            s = math.sin(((1 - t) / 0.12) * math.pi / 2)
        else:
            s = 1.0
        h = hh * (0.65 + 0.35 * s)
        w = hw * (0.92 + 0.08 * s)
        secs.append(oval_section(x, w, cz - h, cz + h, 28, squat=0.95))
    d.add(loft_mesh(secs, True), "AirUnit_Window", "03_AirUnit::Window", "MAT_AirClear", "GRP_Air")

    # Membrane bag
    mem = []
    for i in range(12):
        t = i / 11
        x = cx - hl + 3 + (AIR["length"] - 6) * t
        mem.append(oval_section(x, hw * 0.68, cz - hh * 0.72, cz + hh * 0.72, 24, 0.98))
    d.add(loft_mesh(mem, True), "AirUnit_Membrane", "03_AirUnit::Membrane", "MAT_AirMem", "GRP_Air")

    # 3 vertical pillars (classic AM1)
    for i in range(3):
        t = (i + 1) / 4
        x = cx - hl + AIR["length"] * t
        d.add(
            box_mesh(x - 1.4, -hw * 0.5, cz - hh * 0.78, x + 1.4, hw * 0.5, cz + hh * 0.78),
            f"AirUnit_Pillar_{i+1}",
            "03_AirUnit::Pillars",
            "MAT_AirPillar",
            "GRP_Air",
        )


def build_upper(d: Doc):
    # Primary upper volume — thin rounded last shell (mesh base)
    xs = list(np.linspace(4, L - 4, 46))
    d.add(
        thin_last_shell(xs, thickness=2.2, count=48),
        "Upper_Mesh_Last",
        "04_Upper::MeshBase",
        "MAT_Mesh",
        "GRP_Upper",
        user={"Note": "Main upper last shell — assign mesh material"},
    )

    # Collar pad (thicker band near opening, rear half)
    xs_col = list(np.linspace(4, 125, 26))
    for sign, tag in ((1.0, "Lateral"), (-1.0, "Medial")):
        d.add(
            grid_shell(
                xs_col,
                lambda x: collar_top_z(x) - 16,
                collar_top_z,
                sign,
                n_z=7,
                thickness=3.5,
                width_fn=lambda x, z: upper_half_width(x, z) * 1.02,
            ),
            f"Collar_{tag}",
            "04_Upper::Collar",
            "MAT_Collar",
            "GRP_Upper",
        )

    # Black lining
    xs_lin = list(np.linspace(6, 115, 22))
    for sign, tag in ((1.0, "Lateral"), (-1.0, "Medial")):
        d.add(
            grid_shell(
                xs_lin,
                lambda x: midsole_top_z(x) + 6,
                lambda x: collar_top_z(x) - 3,
                sign,
                n_z=9,
                thickness=1.2,
                width_fn=lambda x, z: upper_half_width(x, z) * 0.86,
            ),
            f"Lining_{tag}",
            "04_Upper::Lining",
            "MAT_Lining",
            "GRP_Upper",
        )


def build_mudguard(d: Doc):
    xs = list(np.linspace(2, L - 2, 48))
    for sign, tag in ((1.0, "Lateral"), (-1.0, "Medial")):
        d.add(
            grid_shell(
                xs,
                lambda x: midsole_top_z(x) - 0.8,
                mudguard_top_z,
                sign,
                n_z=8,
                thickness=1.8,
                width_fn=lambda x, z: sole_half_width(x) * 0.94,
            ),
            f"Mudguard_{tag}",
            "05_Overlays::Mudguard",
            "MAT_LeatherBlk",
            "GRP_Overlays",
            user={"DNA_Mid_mm": 7, "DNA_Heel_mm": 15},
        )
    # Toe mudguard bumper (low wrap over toebox front)
    xs_toe = list(np.linspace(L - 50, L - 3, 16))
    rows = []
    for x in xs_toe:
        hw = sole_half_width(x) * 0.95
        z0 = midsole_top_z(x) - 0.5
        z1 = mudguard_top_z(x)
        row = []
        for j in range(12):
            v = j / 11
            y = lerp(-hw, hw, v)
            edge = min(v, 1 - v) * 2
            z = lerp(z0 + 1.0, z1, 0.25 + 0.75 * math.sin(math.pi * v))
            row.append(pt(x, y, z))
        rows.append(row)
    rows_i = [[pt(p.X, p.Y, max(midsole_top_z(p.X) - 0.2, p.Z - 2.0)) for p in row] for row in rows]
    d.add(loft_pair(rows, rows_i), "Mudguard_ToeCap", "05_Overlays::Mudguard", "MAT_LeatherBlk", "GRP_Overlays")


def build_suede_overlays(d: Doc):
    # Quarter suede above mudguard
    xs = list(np.linspace(70, 200, 32))
    for sign, tag in ((1.0, "Lateral"), (-1.0, "Medial")):
        d.add(
            grid_shell(
                xs,
                lambda x: mudguard_top_z(x) - 1.0,
                lambda x: lerp(mudguard_top_z(x) + 28, collar_top_z(x) - 6, clamp((x - 70) / 130, 0, 1)),
                sign,
                n_z=10,
                thickness=1.4,
            ),
            f"Quarter_Suede_{tag}",
            "05_Overlays::SuedeQuarter",
            "MAT_Suede",
            "GRP_Overlays",
        )

    # Heel counter
    xs_h = list(np.linspace(2, 70, 22))
    for sign, tag in ((1.0, "Lateral"), (-1.0, "Medial")):
        d.add(
            grid_shell(
                xs_h,
                lambda x: mudguard_top_z(x) - 0.5,
                lambda x: collar_top_z(x) - 4,
                sign,
                n_z=10,
                thickness=1.5,
            ),
            f"HeelCounter_{tag}",
            "05_Overlays::HeelCounter",
            "MAT_Suede",
            "GRP_Overlays",
            user={"Branding": "NIKE AIR"},
        )
    # Heel back panel
    secs = []
    for i in range(10):
        x = 1 + i * 2.2
        w = 22 - i * 1.1
        z0 = mudguard_top_z(x) + 2
        z1 = collar_top_z(x) - 2
        secs.append(oval_section(x, w * 0.45, z0, z1, 20, 0.7))
    d.add(loft_mesh(secs, True), "HeelTab", "05_Overlays::HeelCounter", "MAT_Suede", "GRP_Overlays")


def build_swoosh(d: Doc):
    """Nike Swoosh — placed on quarter, proportions from FZ5808-102 lateral."""
    spine = [
        (170, 0.78, 8, 3.5),
        (160, 0.88, 10, 5.5),
        (148, 0.96, 14, 8.5),
        (136, 0.99, 18, 11.0),
        (124, 0.98, 24, 11.5),
        (112, 0.92, 30, 10.0),
        (100, 0.82, 35, 8.0),
        (90, 0.68, 38, 5.5),
        (82, 0.50, 39, 3.5),
        (76, 0.32, 37, 2.0),
    ]
    for sign, tag in ((1.0, "Lateral"), (-1.0, "Medial")):
        secs = []
        for x, yf, zadd, wh in spine:
            y = sign * sole_half_width(x) * yf * 0.92
            z = mudguard_top_z(x) + zadd
            local = []
            for k in range(12):
                a = 2 * math.pi * k / 12
                local.append(pt(x + 1.4 * math.cos(a), y + sign * 0.8, z + wh * math.sin(a)))
            secs.append(local)
        d.add(loft_mesh(secs, True), f"Swoosh_{tag}", "05_Overlays::Swoosh", "MAT_LeatherBlk", "GRP_Overlays")


def build_eyestay_hardware(d: Doc):
    for sign, tag in ((1.0, "Lateral"), (-1.0, "Medial")):
        xs = list(np.linspace(100, 188, 16))
        d.add(
            grid_shell(
                xs,
                lambda x: collar_top_z(x) - 22,
                lambda x: collar_top_z(x) - 2,
                sign,
                n_z=6,
                thickness=1.5,
                width_fn=lambda x, z: 11 + 0.02 * x,
            ),
            f"Eyestay_{tag}",
            "05_Overlays::Eyestay",
            "MAT_Suede",
            "GRP_Overlays",
        )
        for i in range(6):
            x = 108 + i * 13
            y = sign * 11.0
            z = collar_top_z(x) - 12
            d.add(
                cylinder_mesh(pt(x, y - sign * 1.0, z), pt(x, y + sign * 1.0, z), 2.0, 12),
                f"Eyelet_{tag}_{i+1}",
                "06_Hardware::Eyelets",
                "MAT_Plastic",
                "GRP_Hardware",
            )
        # Top lace lock — rounded dual-hole piece (DNA note)
        x, y, z = 102, sign * 11.5, collar_top_z(102) - 8
        d.add(
            box_mesh(x - 5, y - sign * 1.5 - 3.2, z - 4, x + 5, y - sign * 1.5 + 3.2, z + 4),
            f"LaceLock_{tag}",
            "06_Hardware::LaceLock",
            "MAT_Plastic",
            "GRP_Hardware",
        )


def build_softgoods(d: Doc):
    # Tongue — tall padded piece matching product silhouette
    xs = list(np.linspace(105, 215, 24))
    rows = []
    for x in xs:
        t = (x - 105) / 110
        w = lerp(22, 16, t)
        z_top = tongue_top_z(x)
        z_bot = max(collar_top_z(x) - 8, midsole_top_z(x) + 28)
        row = []
        for j, y in enumerate(np.linspace(-w, w, 11)):
            v = j / 10
            crown = math.sin(math.pi * v)
            z = lerp(z_bot, z_top, 0.55 + 0.45 * crown)
            row.append(pt(x, y, z))
        rows.append(row)
    rows_i = [[pt(p.X, p.Y, p.Z - 9.0) for p in row] for row in rows]
    d.add(loft_pair(rows, rows_i), "Tongue", "07_SoftGoods::Tongue", "MAT_Mesh", "GRP_Soft")

    # Tongue label near top
    x_lab = 195
    z_lab = tongue_top_z(x_lab) - 6
    d.add(
        box_mesh(x_lab - 7, -10, z_lab - 1.5, x_lab + 7, 10, z_lab + 1.5),
        "Tongue_Label",
        "07_SoftGoods::TongueLabel",
        "MAT_Label",
        "GRP_Soft",
    )

    for i in range(6):
        x = 112 + i * 14
        z = collar_top_z(x) - 10
        d.add(
            pipe_along_polyline([pt(x, -10.5, z), pt(x + 3, 0, z + 4), pt(x, 10.5, z)], 1.55, 8),
            f"Lace_{i+1}",
            "07_SoftGoods::Laces",
            "MAT_Lace",
            "GRP_Soft",
        )
    # Lace tails
    for sign, tag in ((-1, "L"), (1, "R")):
        z = collar_top_z(110) - 6
        path = [
            pt(110, sign * 10.5, z),
            pt(98, sign * 4, z + 14),
            pt(92, sign * 1, z + 8),
            pt(100, 0, z + 2),
        ]
        d.add(
            pipe_along_polyline(path, 1.6, 8),
            f"Lace_Tail_{tag}",
            "07_SoftGoods::Laces",
            "MAT_Lace",
            "GRP_Soft",
        )

    xs = list(np.linspace(12, L - 18, 28))
    d.add(
        solid_loft_along_x(
            xs,
            lambda x: oval_section(
                x, sole_half_width(x) * 0.75, midsole_top_z(x) + 0.5, midsole_top_z(x) + 4.0, 32, 0.25
            ),
        ),
        "Insole",
        "07_SoftGoods::Insole",
        "MAT_Insole",
        "GRP_Soft",
    )


def main():
    d = Doc()
    setup(d)
    build_profiles(d)
    build_outsole(d)
    build_midsole(d)
    build_air_unit(d)
    build_upper(d)
    build_mudguard(d)
    build_suede_overlays(d)
    build_swoosh(d)
    build_eyestay_hardware(d)
    build_softgoods(d)
    d.save(OUT)
    print(f"Wrote {OUT}")
    print(f"Objects={len(d.doc.Objects)} Layers={len(d.doc.Layers)} Mats={len(d.doc.Materials)} Bytes={OUT.stat().st_size}")


if __name__ == "__main__":
    main()
