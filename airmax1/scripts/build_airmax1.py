#!/usr/bin/env python3
"""
Build a componentized Nike Air Max 1 (Men's US 9, Left) as a Rhino .3dm.

Scale & construction references:
  - Nike DNA archive notes: mudguard 7 mm midfoot / 15–17 mm heel
  - Nike.com Air Max 1 history + Essential product construction
    (mesh/suede/synthetic upper, Max Air heel, waffle outsole)
  - Lab stack/width numbers for men's size scale

Units: millimeters.
Origin: heel at X≈0 on ground Z=0; +X toe; +Y lateral (left shoe); +Z up.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import rhino3dm as r3d

from geometry_utils import (
    box_mesh,
    closed_polyline,
    curve_from_pts,
    cylinder_mesh,
    last_section,
    lerp,
    loft_mesh,
    pipe_along_polyline,
    pt,
    smoothstep,
)


@dataclass(frozen=True)
class AirMax1Spec:
    external_length: float = 295.0
    midsole_width_ff: float = 107.9
    midsole_width_heel: float = 81.8
    heel_stack: float = 32.2
    forefoot_stack: float = 20.1
    outsole_thickness: float = 5.7
    insole_thickness: float = 3.6
    toebox_height: float = 26.5
    tongue_padding: float = 9.0
    mudguard_mid_h: float = 7.0
    mudguard_heel_h: float = 15.0
    mudguard_heel_rear_h: float = 17.0
    air_window_length: float = 48.0
    air_window_height: float = 18.5
    air_window_x_center: float = 42.0
    air_pillar_count: int = 3
    collar_height: float = 78.0
    vamp_height: float = 52.0
    eyelet_count: int = 6


SPEC = AirMax1Spec()
OUT_PATH = Path(__file__).resolve().parents[1] / "output" / "Nike_AirMax1_US9_Left.3dm"


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------

def sole_half_width(x: float, s: AirMax1Spec) -> float:
    t = x / s.external_length
    if t < 0.18:
        return lerp(s.midsole_width_heel * 0.5, s.midsole_width_heel * 0.52, t / 0.18)
    if t < 0.45:
        u = smoothstep((t - 0.18) / 0.27)
        return lerp(s.midsole_width_heel * 0.52, s.midsole_width_ff * 0.48, u)
    if t < 0.78:
        u = smoothstep((t - 0.45) / 0.33)
        return lerp(s.midsole_width_ff * 0.48, s.midsole_width_ff * 0.5, u)
    u = smoothstep((t - 0.78) / 0.22)
    return lerp(s.midsole_width_ff * 0.5, 27.0, u)


def midsole_top_z(x: float, s: AirMax1Spec) -> float:
    t = x / s.external_length
    z = lerp(s.heel_stack, s.forefoot_stack, smoothstep(min(1.0, t / 0.85)))
    if t > 0.88:
        z += 2.8 * smoothstep((t - 0.88) / 0.12)
    return z


def outsole_top_z(x: float, s: AirMax1Spec) -> float:
    return s.outsole_thickness


def mudguard_height(x: float, s: AirMax1Spec) -> float:
    t = x / s.external_length
    if t < 0.12:
        return lerp(s.mudguard_heel_rear_h, s.mudguard_heel_h, t / 0.12)
    if t < 0.35:
        return lerp(s.mudguard_heel_h, s.mudguard_mid_h, (t - 0.12) / 0.23)
    if t < 0.55:
        return s.mudguard_mid_h
    if t < 0.78:
        return lerp(s.mudguard_mid_h, 18.0, (t - 0.55) / 0.23)
    return lerp(18.0, 22.0, (t - 0.78) / 0.22)


def upper_height(x: float, s: AirMax1Spec) -> float:
    t = x / s.external_length
    base = midsole_top_z(x, s)
    if t < 0.12:
        h = s.collar_height - base
    elif t < 0.28:
        h = lerp(s.collar_height, s.vamp_height + 8, (t - 0.12) / 0.16) - base
    elif t < 0.55:
        h = lerp(s.vamp_height + 8, s.vamp_height, (t - 0.28) / 0.27) - base
    elif t < 0.82:
        h = lerp(s.vamp_height, s.toebox_height + 6, (t - 0.55) / 0.27) - base
    else:
        h = lerp(s.toebox_height + 6, 9.0, (t - 0.82) / 0.18) - base
    return max(8.0, h)


def shell_section(
    x: float,
    half_width: float,
    z0: float,
    height: float,
    thickness: float,
    crown: float,
    count: int,
    *,
    z_max: float | None = None,
    z_min: float | None = None,
) -> list:
    """Closed section for a thin shell: outer last slice, then inset return.

    Approximates a hollow panel by using consecutive outer/inner loops as a
    single closed polyline (outer then reversed inner).
    """
    outer = last_section(x, half_width, z0, height, crown=crown, count=count)
    inner = last_section(
        x,
        max(4.0, half_width - thickness),
        z0 + thickness * 0.35,
        max(2.0, height - thickness),
        crown=crown,
        count=count,
    )
    # Optional vertical crop for overlays (mudguard band, etc.)
    if z_max is not None or z_min is not None:
        zlo = z_min if z_min is not None else -1e9
        zhi = z_max if z_max is not None else 1e9

        def crop(pts):
            out = []
            for p in pts:
                z = min(zhi, max(zlo, p.Z))
                out.append(pt(p.X, p.Y, z))
            return out

        outer = crop(outer)
        inner = crop(inner)
    # Build annulus as outer + reversed inner (for solid thin wall loft along X,
    # we instead loft outer and separately loft inner — see thin_shell_loft).
    return outer, inner


def thin_shell_loft(
    xs: list[float],
    outer_fn,
    thickness_hint: float = 1.8,
) -> r3d.Mesh:
    """Loft a thin shell from outer sections and a slightly inset copy."""
    outers = []
    inners = []
    for x in xs:
        outer, inner = outer_fn(x)
        outers.append(outer)
        inners.append(inner)
    # Connect outer loft surface with inner loft by building a solid from
    # concatenated rows: for each x, use outer ring as section via last_section
    # already closed. Create solid by lofting sections that are the outer ring
    # only at first, then use dual surface approach:
    # Practical approach: loft outer, loft inner, then bridge ends — for V-Ray
    # blocking we create a single solid from mid-thickness ring:
    mids = []
    for o, i in zip(outers, inners):
        mid = []
        for a, b in zip(o, i):
            mid.append(pt((a.X + b.X) * 0.5, (a.Y + b.Y) * 0.5, (a.Z + b.Z) * 0.5))
        mids.append(mid)
    # Solid thin volume: loft outer then append reversed inner along length ends
    # Simpler robust method: loft "thick ring" sections (outer points only with
    # small radial thickness baked by using last_section height/width deltas).
    return loft_mesh(outers, cap=True), loft_mesh(inners, cap=False), loft_mesh(mids, cap=True)


# ---------------------------------------------------------------------------
# Document builder
# ---------------------------------------------------------------------------

class DocBuilder:
    def __init__(self) -> None:
        self.doc = r3d.File3dm()
        self.doc.Settings.ModelUnitSystem = r3d.UnitSystem.Millimeters
        self.doc.Settings.ModelAbsoluteTolerance = 0.01
        self.doc.ApplicationName = "AirMax1 Parametric Builder"
        self.doc.ApplicationDetails = "Componentized Nike Air Max 1 for V-Ray"
        self.doc.ApplicationUrl = "https://www.nike.com/a/air-max-1-history"
        self.doc.StartSectionComments = (
            "Nike Air Max 1 — Men's US 9 Left | Units: mm | "
            "Componentized for V-Ray. Sources: Nike DNA / nike.com; lab stack/width refs."
        )
        self.doc.Strings["Project"] = "Nike_AirMax1_US9_Left"
        self.doc.Strings["Size"] = "US9_Men_Left"
        self.doc.Strings["VRay"] = "Materials named MAT_*; assign by object or layer"
        self._layers: dict[str, int] = {}
        self._materials: dict[str, int] = {}
        self._groups: dict[str, int] = {}

    @staticmethod
    def _rgba(rgb: tuple[int, int, int], a: int = 255) -> tuple[int, int, int, int]:
        return (rgb[0], rgb[1], rgb[2], a)

    def layer(self, name: str, color: tuple[int, int, int], parent: str | None = None) -> int:
        if name in self._layers:
            return self._layers[name]
        layer = r3d.Layer()
        layer.Name = name
        layer.Color = self._rgba(color)
        if parent and parent in self._layers:
            layer.ParentLayerId = self.doc.Layers[self._layers[parent]].Id
        idx = self.doc.Layers.Add(layer)
        self._layers[name] = idx
        return idx

    def material(
        self,
        name: str,
        diffuse: tuple[int, int, int],
        *,
        transparency: float = 0.0,
        shine: float = 0.3,
        reflectivity: float = 0.05,
        ior: float = 1.5,
        metallic: float = 0.0,
        roughness: float = 0.55,
        notes: str = "",
    ) -> int:
        if name in self._materials:
            return self._materials[name]
        mat = r3d.Material()
        mat.Name = name
        mat.DiffuseColor = self._rgba(diffuse)
        mat.SpecularColor = (255, 255, 255, 255)
        mat.ReflectionColor = (255, 255, 255, 255)
        mat.Transparency = transparency
        mat.Shine = shine * 255.0
        mat.Reflectivity = reflectivity
        mat.IndexOfRefraction = ior
        if notes:
            mat.SetUserString("VRayHint", notes)
            mat.SetUserString("Roughness", str(roughness))
            mat.SetUserString("Metallic", str(metallic))
        try:
            mat.ToPhysicallyBased()
            pbr = mat.PhysicallyBased
            if pbr is not None:
                pbr.Roughness = roughness
                pbr.Metallic = metallic
                pbr.Opacity = 1.0 - transparency
                if transparency > 0.2:
                    pbr.OpacityIOR = ior
        except Exception:
            pass
        idx = self.doc.Materials.Add(mat)
        self._materials[name] = idx
        return idx

    def group(self, name: str) -> int:
        if name in self._groups:
            return self._groups[name]
        g = r3d.Group()
        g.Name = name
        self.doc.Groups.Add(g)
        found = self.doc.Groups.FindName(name)
        idx = found.Index if found is not None else len(self.doc.Groups) - 1
        self._groups[name] = idx
        return idx

    def add(self, geometry, *, name: str, layer: str, material: str, group: str | None = None, user: dict | None = None) -> None:
        attrs = r3d.ObjectAttributes()
        attrs.Name = name
        attrs.LayerIndex = self._layers[layer]
        attrs.MaterialIndex = self._materials[material]
        attrs.MaterialSource = r3d.ObjectMaterialSource.MaterialFromObject
        if group:
            attrs.AddToGroup(self._groups[group])
        if user:
            for k, v in user.items():
                attrs.SetUserString(k, str(v))
        self.doc.Objects.Add(geometry, attrs)

    def add_curve(self, curve, *, name: str, layer: str) -> None:
        attrs = r3d.ObjectAttributes()
        attrs.Name = name
        attrs.LayerIndex = self._layers[layer]
        self.doc.Objects.AddCurve(curve, attrs)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not self.doc.Write(str(path), 8):
            raise RuntimeError(f"Failed to write {path}")


def setup_document(b: DocBuilder) -> None:
    parents = [
        ("00_Reference", (120, 120, 120)),
        ("01_Sole", (40, 40, 40)),
        ("02_Midsole", (230, 230, 230)),
        ("03_AirUnit", (180, 220, 255)),
        ("04_Upper", (200, 200, 200)),
        ("05_Overlays", (160, 150, 140)),
        ("06_Hardware", (30, 30, 30)),
        ("07_SoftGoods", (240, 240, 240)),
    ]
    for name, col in parents:
        b.layer(name, col)

    children = [
        ("00_Reference::Last_Curves", "00_Reference", (100, 100, 255)),
        ("00_Reference::Dimensions", "00_Reference", (255, 180, 0)),
        ("01_Sole::Outsole_Base", "01_Sole", (20, 20, 20)),
        ("01_Sole::Waffle_Lugs", "01_Sole", (25, 25, 25)),
        ("01_Sole::Toe_Wrap", "01_Sole", (180, 20, 30)),
        ("01_Sole::Heel_Wrap", "01_Sole", (180, 20, 30)),
        ("02_Midsole::Foam_Body", "02_Midsole", (245, 245, 245)),
        ("03_AirUnit::Window", "03_AirUnit", (200, 230, 255)),
        ("03_AirUnit::Membrane", "03_AirUnit", (220, 240, 255)),
        ("03_AirUnit::Pillars", "03_AirUnit", (190, 210, 230)),
        ("04_Upper::Toebox_Mesh", "04_Upper", (250, 250, 250)),
        ("04_Upper::Vamp_Mesh", "04_Upper", (245, 245, 245)),
        ("04_Upper::Quarter_Mesh", "04_Upper", (240, 240, 240)),
        ("04_Upper::Collar", "04_Upper", (235, 235, 235)),
        ("04_Upper::Lining", "04_Upper", (230, 230, 230)),
        ("05_Overlays::Mudguard", "05_Overlays", (25, 25, 25)),
        ("05_Overlays::Quarter_Suede", "05_Overlays", (210, 205, 195)),
        ("05_Overlays::Heel_Counter", "05_Overlays", (205, 200, 190)),
        ("05_Overlays::Heel_Tab", "05_Overlays", (215, 210, 200)),
        ("05_Overlays::Swoosh", "05_Overlays", (15, 15, 15)),
        ("05_Overlays::Eyestay", "05_Overlays", (250, 250, 250)),
        ("06_Hardware::Eyelets", "06_Hardware", (40, 40, 40)),
        ("06_Hardware::Lace_Lock", "06_Hardware", (20, 20, 20)),
        ("07_SoftGoods::Tongue", "07_SoftGoods", (250, 250, 250)),
        ("07_SoftGoods::Tongue_Label", "07_SoftGoods", (255, 255, 255)),
        ("07_SoftGoods::Laces", "07_SoftGoods", (245, 245, 245)),
        ("07_SoftGoods::Insole", "07_SoftGoods", (240, 240, 235)),
    ]
    for name, parent, col in children:
        b.layer(name, col, parent=parent)

    mats = [
        ("MAT_Rubber_Outsole", (18, 18, 18), dict(shine=0.25, roughness=0.65, notes="V-Ray black rubber")),
        ("MAT_Rubber_Accent", (170, 25, 35), dict(shine=0.3, roughness=0.55, notes="OG University Red wrap")),
        ("MAT_Foam_Midsole", (245, 245, 242), dict(shine=0.15, roughness=0.75, notes="Phylon foam, matte SSS optional")),
        ("MAT_Air_Clear", (210, 230, 245), dict(transparency=0.72, shine=0.85, reflectivity=0.15, ior=1.49, roughness=0.05, notes="Clear TPU window IOR~1.49")),
        ("MAT_Air_Membrane", (200, 215, 230), dict(transparency=0.35, shine=0.4, roughness=0.25, notes="Translucent air bag")),
        ("MAT_Air_Pillar", (185, 200, 215), dict(transparency=0.25, shine=0.5, roughness=0.2, notes="Visible Air ribs")),
        ("MAT_Mesh_Upper", (248, 248, 246), dict(shine=0.1, roughness=0.8, notes="Engineered mesh + weave maps")),
        ("MAT_Suede_Overlay", (208, 202, 190), dict(shine=0.05, roughness=0.9, notes="Nubuck/suede bone")),
        ("MAT_Synthetic_Mudguard", (22, 22, 22), dict(shine=0.35, roughness=0.45, notes="Synthetic leather mudguard")),
        ("MAT_Synthetic_Swoosh", (12, 12, 12), dict(shine=0.4, roughness=0.4, notes="Swoosh overlay")),
        ("MAT_Collar_Textile", (236, 236, 234), dict(shine=0.08, roughness=0.85, notes="Padded collar textile")),
        ("MAT_Plastic_Hardware", (28, 28, 28), dict(shine=0.55, roughness=0.3, metallic=0.05, notes="Lace lock / eyelets")),
        ("MAT_Lace", (242, 242, 240), dict(shine=0.12, roughness=0.7, notes="Flat woven lace")),
        ("MAT_Tongue_Label", (250, 250, 250), dict(shine=0.2, roughness=0.5, notes="Woven tongue label")),
        ("MAT_Insole", (235, 232, 225), dict(shine=0.1, roughness=0.8, notes="Removable sockliner")),
    ]
    for name, diff, kw in mats:
        b.material(name, diff, **kw)

    for g in ("GRP_Outsole", "GRP_Midsole", "GRP_AirUnit", "GRP_Upper", "GRP_Overlays", "GRP_Hardware", "GRP_SoftGoods"):
        b.group(g)


def band_section(x, hw, z0, z1, count=36):
    """Low wrap band between z0 and z1 (mudguard-like)."""
    pts = []
    # bottom lateral -> toe-ish not needed; full perimeter at mid height with vertical extent
    # Represent as last_section cropped
    h = max(1.5, z1 - z0)
    return last_section(x, hw, z0, h, crown=0.08, count=count)


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------

def build_outsole(b: DocBuilder, s: AirMax1Spec) -> None:
    xs = [i * s.external_length / 28 for i in range(29)]
    sections = [
        last_section(x, sole_half_width(x, s), 0.1, outsole_top_z(x, s) - 0.1, crown=0.12, count=40)
        for x in xs
    ]
    b.add(
        loft_mesh(sections, cap=True),
        name="Outsole_Base",
        layer="01_Sole::Outsole_Base",
        material="MAT_Rubber_Outsole",
        group="GRP_Outsole",
        user={"Component": "Outsole", "VRayMaterial": "Rubber_Black"},
    )

    lug_h = 2.8
    for ix in range(6):
        for iy in range(-3, 4):
            x = 155 + ix * 14
            y = iy * 11.5
            if abs(y) > sole_half_width(x, s) - 8:
                continue
            b.add(
                box_mesh(x - 3.75, y - 3.75, 0.0, x + 3.75, y + 3.75, lug_h),
                name=f"Waffle_FF_{ix}_{iy}",
                layer="01_Sole::Waffle_Lugs",
                material="MAT_Rubber_Outsole",
                group="GRP_Outsole",
            )
    for ix in range(3):
        for iy in range(-2, 3):
            x = 18 + ix * 16
            y = iy * 12
            if abs(y) > sole_half_width(x, s) - 6:
                continue
            b.add(
                box_mesh(x - 6, y - 5.5, 0.0, x + 6, y + 5.5, lug_h + 0.4),
                name=f"Waffle_Heel_{ix}_{iy}",
                layer="01_Sole::Waffle_Lugs",
                material="MAT_Rubber_Outsole",
                group="GRP_Outsole",
            )

    toe_xs = [s.external_length - 38 + i * 4 for i in range(10) if s.external_length - 38 + i * 4 < s.external_length - 1]
    b.add(
        loft_mesh(
            [last_section(x, sole_half_width(x, s) * 1.01, 0.3, outsole_top_z(x, s) + 3.2, crown=0.15, count=36) for x in toe_xs],
            cap=True,
        ),
        name="Outsole_Toe_Wrap",
        layer="01_Sole::Toe_Wrap",
        material="MAT_Rubber_Accent",
        group="GRP_Outsole",
        user={"OGColor": "UniversityRed"},
    )
    heel_xs = [i * 4.0 for i in range(10)]
    b.add(
        loft_mesh(
            [last_section(x, sole_half_width(x, s) * 1.01, 0.3, outsole_top_z(x, s) + 2.2, crown=0.15, count=36) for x in heel_xs],
            cap=True,
        ),
        name="Outsole_Heel_Wrap",
        layer="01_Sole::Heel_Wrap",
        material="MAT_Rubber_Accent",
        group="GRP_Outsole",
        user={"OGColor": "UniversityRed"},
    )


def build_midsole(b: DocBuilder, s: AirMax1Spec) -> None:
    xs = [i * s.external_length / 32 for i in range(33)]
    sections = []
    for x in xs:
        z0 = outsole_top_z(x, s) - 0.2
        z1 = midsole_top_z(x, s)
        sections.append(
            last_section(x, sole_half_width(x, s) * 0.99, z0, max(4.0, z1 - z0), crown=0.22, count=44)
        )
    b.add(
        loft_mesh(sections, cap=True),
        name="Midsole_Foam",
        layer="02_Midsole::Foam_Body",
        material="MAT_Foam_Midsole",
        group="GRP_Midsole",
        user={
            "HeelStack_mm": s.heel_stack,
            "ForefootStack_mm": s.forefoot_stack,
            "Drop_mm": round(s.heel_stack - s.forefoot_stack, 2),
        },
    )


def build_air_unit(b: DocBuilder, s: AirMax1Spec) -> None:
    cx = s.air_window_x_center
    half_l = s.air_window_length * 0.5
    half_h = s.air_window_height * 0.5
    z_mid = outsole_top_z(cx, s) + (midsole_top_z(cx, s) - outsole_top_z(cx, s)) * 0.42
    hw = sole_half_width(cx, s)

    secs = []
    for i in range(12):
        t = i / 11
        x = cx - half_l + s.air_window_length * t
        rx = 1.0
        if t < 0.12:
            rx = math.sin((t / 0.12) * math.pi / 2)
        elif t > 0.88:
            rx = math.sin(((1 - t) / 0.12) * math.pi / 2)
        h = half_h * (0.7 + 0.3 * rx)
        secs.append(last_section(x, hw * 0.91, z_mid - h, h * 2, crown=0.9, count=36))
    b.add(
        loft_mesh(secs, cap=True),
        name="AirUnit_Window",
        layer="03_AirUnit::Window",
        material="MAT_Air_Clear",
        group="GRP_AirUnit",
        user={"Component": "MaxAir_Window", "Note": "1987 visible Air — refractive clear TPU"},
    )

    mem = []
    for i in range(10):
        t = i / 9
        x = cx - half_l + 3 + (s.air_window_length - 6) * t
        h = half_h * 0.75
        mem.append(last_section(x, hw * 0.70, z_mid - h, h * 2, crown=0.92, count=32))
    b.add(
        loft_mesh(mem, cap=True),
        name="AirUnit_Membrane",
        layer="03_AirUnit::Membrane",
        material="MAT_Air_Membrane",
        group="GRP_AirUnit",
    )

    for i in range(s.air_pillar_count):
        t = (i + 1) / (s.air_pillar_count + 1)
        x = cx - half_l + s.air_window_length * t
        b.add(
            box_mesh(x - 1.5, -hw * 0.52, z_mid - half_h * 0.82, x + 1.5, hw * 0.52, z_mid + half_h * 0.82),
            name=f"AirUnit_Pillar_{i+1}",
            layer="03_AirUnit::Pillars",
            material="MAT_Air_Pillar",
            group="GRP_AirUnit",
        )


def build_upper_shells(b: DocBuilder, s: AirMax1Spec) -> None:
    """Upper as thinner regional shells (not full solid last)."""

    def region(x0, x1, layer, mat, name, width_scale=0.90, height_scale=1.0, thick=2.2, crown=0.55):
        xs = []
        x = x0
        while x <= x1:
            xs.append(x)
            x += 4.0
        if xs[-1] < x1:
            xs.append(x1)
        # Thin solid via outer section with reduced height and slight inset mid ring
        sections = []
        for x in xs:
            hw = sole_half_width(x, s) * width_scale
            z0 = midsole_top_z(x, s) - 0.3
            h = upper_height(x, s) * height_scale
            # Use a "wall" thickness by lofting a mid-radius section (visual shell)
            sections.append(last_section(x, hw, z0, max(6.0, h), crown=crown, count=48))
        # Create shell look: add outer and a second inset loft as lining partner only for full upper
        b.add(
            loft_mesh(sections, cap=True),
            name=name,
            layer=layer,
            material=mat,
            group="GRP_Upper",
            user={"Component": name, "ThicknessHint_mm": thick},
        )

    region(0, 58, "04_Upper::Collar", "MAT_Collar_Textile", "Upper_Collar_Zone", 0.88, 1.0, 3.0, 0.6)
    region(48, 135, "04_Upper::Quarter_Mesh", "MAT_Mesh_Upper", "Upper_Quarter_Mesh", 0.89, 0.92, 2.0, 0.55)
    region(125, 225, "04_Upper::Vamp_Mesh", "MAT_Mesh_Upper", "Upper_Vamp_Mesh", 0.90, 0.88, 2.0, 0.5)
    region(210, s.external_length - 2, "04_Upper::Toebox_Mesh", "MAT_Mesh_Upper", "Upper_Toebox_Mesh", 0.91, 0.75, 2.0, 0.45)

    # Lining inset
    xs = [i * 3.5 for i in range(20)]
    lining = [
        last_section(
            x,
            sole_half_width(x, s) * 0.80,
            midsole_top_z(x, s) + 1.2,
            upper_height(x, s) * 0.82,
            crown=0.6,
            count=40,
        )
        for x in xs
    ]
    b.add(
        loft_mesh(lining, cap=True),
        name="Upper_Lining",
        layer="04_Upper::Lining",
        material="MAT_Collar_Textile",
        group="GRP_Upper",
    )


def build_mudguard(b: DocBuilder, s: AirMax1Spec) -> None:
    xs = [i * s.external_length / 40 for i in range(41)]
    sections = []
    for x in xs:
        z0 = midsole_top_z(x, s) - 0.8
        h = mudguard_height(x, s)
        # Keep mudguard as a low band — critical AM1 read
        sections.append(
            band_section(x, sole_half_width(x, s) * 0.935, z0, z0 + h, count=44)
        )
    b.add(
        loft_mesh(sections, cap=True),
        name="Mudguard",
        layer="05_Overlays::Mudguard",
        material="MAT_Synthetic_Mudguard",
        group="GRP_Overlays",
        user={
            "DNA_MidHeight_mm": s.mudguard_mid_h,
            "DNA_HeelHeight_mm": s.mudguard_heel_h,
            "DNA_HeelRear_mm": s.mudguard_heel_rear_h,
        },
    )


def build_quarter_and_heel(b: DocBuilder, s: AirMax1Spec) -> None:
    xs = [72 + i * 4 for i in range(26)]
    secs = []
    for x in xs:
        t = (x - 72) / 100
        z0 = midsole_top_z(x, s) + mudguard_height(x, s) * 0.85
        h = max(8.0, upper_height(x, s) * lerp(0.42, 0.28, t))
        secs.append(last_section(x, sole_half_width(x, s) * 0.905, z0, h, crown=0.4, count=40))
    b.add(
        loft_mesh(secs, cap=True),
        name="Quarter_Suede_Overlay",
        layer="05_Overlays::Quarter_Suede",
        material="MAT_Suede_Overlay",
        group="GRP_Overlays",
        user={"VRayMaterial": "Suede_Bone"},
    )

    xs_h = [i * 3.2 for i in range(17)]
    secs_h = []
    for x in xs_h:
        z0 = midsole_top_z(x, s) + mudguard_height(x, s) * 0.7
        h = max(10.0, upper_height(x, s) * lerp(0.62, 0.38, x / 55))
        secs_h.append(last_section(x, sole_half_width(x, s) * 0.91, z0, h, crown=0.48, count=40))
    b.add(
        loft_mesh(secs_h, cap=True),
        name="Heel_Counter",
        layer="05_Overlays::Heel_Counter",
        material="MAT_Suede_Overlay",
        group="GRP_Overlays",
        user={"Branding": "NIKE AIR"},
    )

    tab = []
    for i in range(8):
        x = 2 + i * 2.0
        tab.append(
            last_section(
                x,
                (16 - i * 0.7) * 0.5,
                midsole_top_z(x, s) + 30,
                20 - i * 1.1,
                crown=0.7,
                count=24,
            )
        )
    b.add(
        loft_mesh(tab, cap=True),
        name="Heel_Tab",
        layer="05_Overlays::Heel_Tab",
        material="MAT_Suede_Overlay",
        group="GRP_Overlays",
    )


def build_swoosh(b: DocBuilder, s: AirMax1Spec) -> None:
    samples = [
        (178, 0.72, 9, 5.0),
        (168, 0.84, 11, 7.5),
        (155, 0.94, 14, 11.0),
        (140, 0.99, 19, 13.5),
        (125, 0.97, 25, 13.0),
        (110, 0.90, 31, 11.0),
        (98, 0.78, 36, 8.5),
        (88, 0.62, 39, 6.0),
        (80, 0.45, 38, 3.5),
    ]

    for lateral, tag in ((True, "Lateral"), (False, "Medial")):
        sign = 1.0 if lateral else -1.0
        secs = []
        for x, yf, zadd, w in samples:
            y = sign * sole_half_width(x, s) * yf
            z = midsole_top_z(x, s) + zadd
            local = []
            for k in range(14):
                a = 2 * math.pi * k / 14
                local.append(
                    pt(
                        x + 1.4 * math.cos(a),
                        y + sign * 0.9 * abs(math.cos(a)) * 0.15,
                        z + (w * 0.5) * math.sin(a),
                    )
                )
            secs.append(local)
        b.add(
            loft_mesh(secs, cap=True),
            name=f"Swoosh_{tag}",
            layer="05_Overlays::Swoosh",
            material="MAT_Synthetic_Swoosh",
            group="GRP_Overlays",
            user={"Side": tag},
        )


def build_eyestay_and_hardware(b: DocBuilder, s: AirMax1Spec) -> None:
    for sign, side in ((1.0, "Lateral"), (-1.0, "Medial")):
        secs = []
        for i in range(12):
            x = 95 + i * 8
            y = sign * (11.5 + i * 0.12)
            z0 = midsole_top_z(x, s) + upper_height(x, s) * 0.58
            secs.append(
                [
                    pt(x - 3, y - sign * 1.5, z0),
                    pt(x + 3, y - sign * 1.5, z0),
                    pt(x + 3, y + sign * 3.5, z0 + 7),
                    pt(x - 3, y + sign * 3.5, z0 + 7),
                ]
            )
        b.add(
            loft_mesh(secs, cap=True),
            name=f"Eyestay_{side}",
            layer="05_Overlays::Eyestay",
            material="MAT_Mesh_Upper",
            group="GRP_Overlays",
        )

        for i in range(s.eyelet_count):
            x = 105 + i * 12
            y = sign * 10.5
            z = midsole_top_z(x, s) + upper_height(x, s) * 0.72
            b.add(
                cylinder_mesh(pt(x, y - sign * 1.1, z), pt(x, y + sign * 1.1, z), 2.1, 14),
                name=f"Eyelet_{side}_{i+1}",
                layer="06_Hardware::Eyelets",
                material="MAT_Plastic_Hardware",
                group="GRP_Hardware",
            )

        x, y = 100, sign * 11
        z = midsole_top_z(x, s) + upper_height(x, s) * 0.78
        b.add(
            box_mesh(x - 4.5, y - sign * 1.2 - 2.8, z - 3.5, x + 4.5, y - sign * 1.2 + 2.8, z + 3.5),
            name=f"LaceLock_{side}",
            layer="06_Hardware::Lace_Lock",
            material="MAT_Plastic_Hardware",
            group="GRP_Hardware",
            user={"DNA": "Rounded outline, smaller holes"},
        )


def build_tongue_laces_insole(b: DocBuilder, s: AirMax1Spec) -> None:
    secs = []
    for i in range(14):
        x = 112 + i * 7
        w = lerp(26, 20, i / 13)
        z0 = midsole_top_z(x, s) + upper_height(x, s) * 0.88
        secs.append(last_section(x, w * 0.5, z0, s.tongue_padding, crown=0.85, count=28))
    b.add(
        loft_mesh(secs, cap=True),
        name="Tongue",
        layer="07_SoftGoods::Tongue",
        material="MAT_Mesh_Upper",
        group="GRP_SoftGoods",
        user={"Padding_mm": s.tongue_padding},
    )

    zlab = midsole_top_z(200, s) + 50
    b.add(
        box_mesh(196, -11, zlab, 209, 11, zlab + 3.5),
        name="Tongue_Label",
        layer="07_SoftGoods::Tongue_Label",
        material="MAT_Tongue_Label",
        group="GRP_SoftGoods",
    )

    for i in range(s.eyelet_count):
        x = 105 + i * 12
        z = midsole_top_z(x, s) + upper_height(x, s) * 0.74
        b.add(
            pipe_along_polyline([pt(x, -10.5, z), pt(x, 0, z + 2.5), pt(x, 10.5, z)], 1.55, 8),
            name=f"Lace_Cross_{i+1}",
            layer="07_SoftGoods::Laces",
            material="MAT_Lace",
            group="GRP_SoftGoods",
        )
    for sign, tag in ((-1, "L"), (1, "R")):
        path = [
            pt(105, sign * 10.5, midsole_top_z(105, s) + 55),
            pt(94, sign * 5, midsole_top_z(94, s) + 61),
            pt(88, sign * 1.5, midsole_top_z(88, s) + 57),
            pt(96, 0, midsole_top_z(96, s) + 51),
        ]
        b.add(
            pipe_along_polyline(path, 1.65, 8),
            name=f"Lace_Tail_{tag}",
            layer="07_SoftGoods::Laces",
            material="MAT_Lace",
            group="GRP_SoftGoods",
        )

    xs = [18 + i * (s.external_length - 40) / 24 for i in range(25)]
    secs = [
        last_section(
            x,
            sole_half_width(x, s) * 0.76,
            midsole_top_z(x, s) + 0.5,
            s.insole_thickness,
            crown=0.18,
            count=36,
        )
        for x in xs
    ]
    b.add(
        loft_mesh(secs, cap=True),
        name="Insole",
        layer="07_SoftGoods::Insole",
        material="MAT_Insole",
        group="GRP_SoftGoods",
        user={"Removable": True},
    )


def build_reference(b: DocBuilder, s: AirMax1Spec) -> None:
    center = [pt(x, 0, midsole_top_z(x, s)) for x in range(0, int(s.external_length) + 1, 10)]
    b.add_curve(curve_from_pts(center, 3), name="Last_Centerline", layer="00_Reference::Last_Curves")
    side = [
        pt(x, sole_half_width(x, s), midsole_top_z(x, s) + mudguard_height(x, s))
        for x in range(0, int(s.external_length) + 1, 5)
    ]
    b.add_curve(curve_from_pts(side, 3), name="Mudguard_Crest_Lateral", layer="00_Reference::Last_Curves")

    dims = [
        ("Dim_Length", [pt(0, -55, 0), pt(s.external_length, -55, 0)]),
        ("Dim_HeelStack", [pt(25, 0, 0), pt(25, 0, s.heel_stack)]),
        ("Dim_FFStack", [pt(230, 0, 0), pt(230, 0, s.forefoot_stack)]),
        ("Dim_HeelWidth", [pt(40, -s.midsole_width_heel / 2, s.heel_stack), pt(40, s.midsole_width_heel / 2, s.heel_stack)]),
        ("Dim_FFWidth", [pt(210, -s.midsole_width_ff / 2, s.forefoot_stack), pt(210, s.midsole_width_ff / 2, s.forefoot_stack)]),
        ("Dim_Mudguard_Mid", [pt(140, sole_half_width(140, s), midsole_top_z(140, s)), pt(140, sole_half_width(140, s), midsole_top_z(140, s) + s.mudguard_mid_h)]),
        ("Dim_Mudguard_Heel", [pt(30, sole_half_width(30, s), midsole_top_z(30, s)), pt(30, sole_half_width(30, s), midsole_top_z(30, s) + s.mudguard_heel_h)]),
    ]
    for name, pts in dims:
        b.add_curve(curve_from_pts(pts, 1), name=name, layer="00_Reference::Dimensions")


def main() -> None:
    s = SPEC
    b = DocBuilder()
    setup_document(b)
    build_reference(b, s)
    build_outsole(b, s)
    build_midsole(b, s)
    build_air_unit(b, s)
    build_upper_shells(b, s)
    build_mudguard(b, s)
    build_quarter_and_heel(b, s)
    build_swoosh(b, s)
    build_eyestay_and_hardware(b, s)
    build_tongue_laces_insole(b, s)
    b.save(OUT_PATH)
    print(f"Wrote {OUT_PATH}")
    print(f"Objects: {len(b.doc.Objects)}  Layers: {len(b.doc.Layers)}  Materials: {len(b.doc.Materials)}  Bytes: {OUT_PATH.stat().st_size}")


if __name__ == "__main__":
    main()
