"""Write a Rhino .3dm with the pendant body, lattice curves, and hanger.

This does not perform solid booleans (openNURBS cannot). Open the file in
Rhino and run scale_pendant.py to cut the lattice, or Extrude + BooleanDifference
the curves yourself.
"""

from __future__ import annotations

import math
from pathlib import Path

import rhino3dm as r3d

import params as P
from lattice import iter_holes, superellipse_points
from outline import rounded_rect_points

OUT = Path(__file__).resolve().parent / "scale_pendant.3dm"


def _layer(name, r, g, b, visible=True):
    layer = r3d.Layer()
    layer.Name = name
    layer.Color = (r, g, b, 255)
    layer.Visible = visible
    return layer


def _attr(layer_index, name=None):
    attr = r3d.ObjectAttributes()
    attr.LayerIndex = layer_index
    if name:
        attr.Name = name
    return attr


def closed_polyline(points_xy, z=0.0):
    pts = [r3d.Point3d(x, y, z) for x, y in points_xy]
    pts.append(pts[0])
    return r3d.Polyline(pts)


def main():
    f = r3d.File3dm()
    f.Settings.ModelUnitSystem = r3d.UnitSystem.Millimeters
    f.Settings.ModelAbsoluteTolerance = 0.01

    layers = [
        _layer(P.LAYER_CONSTRUCTION, 160, 160, 160, visible=False),
        _layer(P.LAYER_BODY, 196, 196, 204),
        _layer(P.LAYER_LATTICE, 90, 90, 100),
        _layer(P.LAYER_POCKETS, 70, 70, 78),
        _layer(P.LAYER_HARDWARE, 210, 210, 220),
    ]
    for layer in layers:
        f.Layers.Add(layer)
    index = {layer.Name: i for i, layer in enumerate(layers)}

    outline = closed_polyline(rounded_rect_points(P.WIDTH, P.HEIGHT, P.CORNER_RADIUS, 16))
    outline_crv = r3d.PolylineCurve(outline)
    f.Objects.AddCurve(outline_crv, _attr(index[P.LAYER_CONSTRUCTION], "outline"))

    body = r3d.Extrusion.Create(outline_crv, P.THICKNESS, True)
    if body is not None:
        f.Objects.AddExtrusion(body, _attr(index[P.LAYER_BODY], "body-solid"))

    n_through = n_pocket = 0
    for cx, cy, rx, ry, scale in iter_holes(min_scale=0.08):
        poly = closed_polyline(superellipse_points(cx, cy, rx, ry, P.SUPERELLIPSE_N, 64))
        crv = r3d.PolylineCurve(poly)
        height_norm = (cy + P.HEIGHT * 0.5) / P.HEIGHT
        if height_norm >= P.BLIND_POCKET_BELOW and scale >= 0.35:
            f.Objects.AddCurve(crv, _attr(index[P.LAYER_LATTICE], "through-cell"))
            n_through += 1
        else:
            f.Objects.AddCurve(crv, _attr(index[P.LAYER_POCKETS], "pocket-cell"))
            n_pocket += 1

    sphere = r3d.Sphere(
        r3d.Point3d(0.0, P.HEIGHT * 0.5, P.THICKNESS * 0.5),
        P.HANGER_SPHERE_R,
    )
    f.Objects.AddSphere(sphere, _attr(index[P.LAYER_HARDWARE], "hanger-sphere"))

    stem_circle = r3d.Circle(r3d.Point3d(0.0, 0.0, 0.0), P.STEM_R)
    stem_cyl = r3d.Cylinder(stem_circle, P.STEM_H)
    stem = r3d.Extrusion.CreateCylinderExtrusion(stem_cyl, True, True)
    if stem is not None:
        origin = r3d.Point3d(0.0, 0.0, 0.0)
        stem.Rotate(-math.pi / 2.0, r3d.Vector3d(1.0, 0.0, 0.0), origin)
        stem.Translate(r3d.Vector3d(0.0, P.HEIGHT * 0.5, P.THICKNESS * 0.5))
        f.Objects.AddExtrusion(stem, _attr(index[P.LAYER_HARDWARE], "hanger-stem"))

    note = (
        "Scale-lattice pendant (mm)\n"
        "Run scale_pendant.py in Rhino 8 to boolean the lattice.\n"
        "Through-holes: {}   Fade pockets: {}".format(n_through, n_pocket)
    )
    f.Objects.AddTextDot(note, r3d.Point3d(0.0, -P.HEIGHT * 0.5 - 30.0, 0.0))

    f.Write(str(OUT), 8)
    print("wrote {}  through={} pockets={}".format(OUT, n_through, n_pocket))


if __name__ == "__main__":
    main()
