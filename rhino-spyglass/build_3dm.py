"""Write spyglass.3dm — stylized wooden telescope."""

from __future__ import annotations

import math
from pathlib import Path

import rhino3dm as r3d

import params as P
from geom import box_xyz, cylinder_x, frustum_x, pipe_x, prism_x

OUT = Path(__file__).resolve().parent / "spyglass.3dm"


def _layer(name, color, visible=True):
    layer = r3d.Layer()
    layer.Name = name
    layer.Color = color
    layer.Visible = visible
    return layer


def _attr(layer_index, name, color, material_index):
    attr = r3d.ObjectAttributes()
    attr.LayerIndex = layer_index
    attr.Name = name
    attr.ColorSource = r3d.ObjectColorSource.ColorFromObject
    attr.ObjectColor = color
    attr.MaterialSource = r3d.ObjectMaterialSource.MaterialFromObject
    attr.MaterialIndex = material_index
    return attr


def add_mat(f, name, diffuse, transparency=0.0, ior=1.0, reflect=0.0):
    mat = r3d.Material()
    mat.Name = name
    mat.DiffuseColor = diffuse
    mat.Transparency = transparency
    mat.IndexOfRefraction = ior
    mat.Reflectivity = reflect
    return f.Materials.Add(mat)


def add_geom(f, geom, layer_i, name, color, mat_i):
    if geom is None:
        return
    attr = _attr(layer_i, name, color, mat_i)
    if isinstance(geom, r3d.Brep):
        f.Objects.AddBrep(geom, attr)
    else:
        f.Objects.AddExtrusion(geom, attr)


def main():
    f = r3d.File3dm()
    f.Settings.ModelUnitSystem = r3d.UnitSystem.Millimeters
    f.Settings.ModelAbsoluteTolerance = 0.01

    layers = [
        _layer(P.LAYER_CONSTRUCTION, (160, 160, 160, 255), False),
        _layer(P.LAYER_GOLD, P.GOLD),
        _layer(P.LAYER_CHROME, P.CHROME),
        _layer(P.LAYER_COLLAR, P.COLLAR),
        _layer(P.LAYER_WOOD, P.WOOD),
        _layer(P.LAYER_LENS, P.LENS),
        _layer(P.LAYER_SIGHT, P.WOOD),
    ]
    for layer in layers:
        f.Layers.Add(layer)
    idx = {layer.Name: i for i, layer in enumerate(layers)}

    m_gold = add_mat(f, "gold", P.GOLD, reflect=0.35)
    m_chrome = add_mat(f, "chrome", P.CHROME, reflect=0.7)
    m_collar = add_mat(f, "leather", P.COLLAR)
    m_wood = add_mat(f, "wood", P.WOOD)
    m_wood_dark = add_mat(f, "wood-endgrain", P.WOOD_DARK)
    m_lens = add_mat(f, "glass-cyan", P.LENS, transparency=0.35, ior=1.5)

    add_geom(f, cylinder_x(P.EYE_X, P.EYE_L, P.EYE_R), idx[P.LAYER_GOLD], "eyepiece", P.GOLD, m_gold)
    add_geom(
        f,
        cylinder_x(P.SILVER_X, P.SILVER_L, P.SILVER_R),
        idx[P.LAYER_CHROME],
        "draw-tube",
        P.CHROME,
        m_chrome,
    )
    add_geom(
        f,
        prism_x(P.COLLAR_X, P.COLLAR_L, P.COLLAR_R, P.COLLAR_SIDES, rotation=math.pi / P.COLLAR_SIDES),
        idx[P.LAYER_COLLAR],
        "collar",
        P.COLLAR,
        m_collar,
    )
    add_geom(
        f,
        frustum_x(P.BARREL_X0, P.BARREL_X1, P.BARREL_R0, P.BARREL_R1),
        idx[P.LAYER_WOOD],
        "barrel",
        P.WOOD,
        m_wood,
    )
    add_geom(
        f,
        pipe_x(P.RIM_X, P.RIM_L, P.RIM_R_OUT, P.RIM_R_IN),
        idx[P.LAYER_WOOD],
        "objective-rim",
        P.WOOD_DARK,
        m_wood_dark,
    )
    add_geom(
        f,
        pipe_x(P.RING_X, P.RING_L, P.RING_R_OUT, P.RING_R_IN),
        idx[P.LAYER_GOLD],
        "lens-ring",
        P.GOLD,
        m_gold,
    )
    add_geom(
        f,
        cylinder_x(P.LENS_X, P.LENS_L, P.LENS_R),
        idx[P.LAYER_LENS],
        "lens",
        P.LENS,
        m_lens,
    )
    add_geom(
        f,
        box_xyz(P.SIGHT_X0, P.SIGHT_X1, P.SIGHT_Y0, P.SIGHT_Y1, P.SIGHT_Z0, P.SIGHT_Z1),
        idx[P.LAYER_SIGHT],
        "sight",
        P.WOOD,
        m_wood,
    )

    f.Objects.AddTextDot(
        "Stylized spyglass (mm)\nRun spyglass.py in Rhino 8 to rebuild.\nApply a wood texture to 04_Wood for grain.",
        r3d.Point3d(P.BARREL_X0, -P.BARREL_R1 - 20.0, 0.0),
    )
    f.Write(str(OUT), 8)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
