#! python 3
"""
Stylized wooden spyglass for Rhino 8.

ScriptEditor → Open this file → Run
or _-RunPythonScript and pick this file.
"""

from __future__ import annotations

import math
import os
import sys

import Rhino
import Rhino.Geometry as rg
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System
from System.Drawing import Color

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import params as P


def log(msg):
    Rhino.RhinoApp.WriteLine("[spyglass] " + str(msg))


def ensure_layer(name, color, visible=True):
    if not rs.IsLayer(name):
        rs.AddLayer(name, color=color)
    rs.LayerVisible(name, visible)
    return name


def add_brep(brep, layer, name):
    if brep is None:
        return None
    oid = sc.doc.Objects.AddBrep(brep)
    if oid == System.Guid.Empty:
        return None
    rs.ObjectLayer(oid, layer)
    rs.ObjectName(oid, name)
    rs.ObjectColor(oid, _color(name, layer))
    return oid


def _color(name, layer):
    mapping = {
        P.LAYER_GOLD: Color.FromArgb(*P.GOLD[:3]),
        P.LAYER_CHROME: Color.FromArgb(*P.CHROME[:3]),
        P.LAYER_COLLAR: Color.FromArgb(*P.COLLAR[:3]),
        P.LAYER_WOOD: Color.FromArgb(*P.WOOD[:3]),
        P.LAYER_LENS: Color.FromArgb(*P.LENS[:3]),
        P.LAYER_SIGHT: Color.FromArgb(*P.WOOD[:3]),
    }
    if name == "objective-rim":
        return Color.FromArgb(*P.WOOD_DARK[:3])
    return mapping.get(layer, Color.Gray)


def cylinder_x(x0, length, radius):
    plane = rg.Plane(rg.Point3d(x0, 0, 0), rg.Vector3d.XAxis)
    cyl = rg.Cylinder(rg.Circle(plane, radius), length)
    ext = rg.Extrusion.CreateCylinderExtrusion(cyl, True, True)
    return ext.ToBrep() if ext else None


def pipe_x(x0, length, r_out, r_in):
    plane = rg.Plane(rg.Point3d(x0, 0, 0), rg.Vector3d.XAxis)
    cyl = rg.Cylinder(rg.Circle(plane, r_out), length)
    ext = rg.Extrusion.CreatePipeExtrusion(cyl, r_in, True, True)
    return ext.ToBrep() if ext else None


def frustum_x(x0, x1, r0, r1):
    profile = rg.LineCurve(rg.Point3d(x0, r0, 0), rg.Point3d(x1, r1, 0))
    axis = rg.Line(rg.Point3d(x0, 0, 0), rg.Point3d(x1, 0, 0))
    rev = rg.RevSurface.Create(profile, axis, 0.0, 2.0 * math.pi)
    if rev is None:
        return None
    return rg.Brep.CreateFromRevSurface(rev, True, True)


def prism_x(x0, length, radius, sides, rotation=0.0):
    pts = []
    for i in range(sides + 1):
        a = rotation + 2.0 * math.pi * i / sides
        pts.append(rg.Point3d(x0, radius * math.cos(a), radius * math.sin(a)))
    crv = rg.Polyline(pts).ToNurbsCurve()
    if crv is None:
        return None
    ext = rg.Extrusion.Create(crv, length, True)
    return ext.ToBrep() if ext else None


def box_xyz(x0, x1, y0, y1, z0, z1):
    box = rg.BoundingBox(rg.Point3d(x0, y0, z0), rg.Point3d(x1, y1, z1))
    return rg.Brep.CreateFromBox(box)


def setup_doc():
    sc.doc.ModelUnitSystem = Rhino.UnitSystem.Millimeters
    ensure_layer(P.LAYER_CONSTRUCTION, Color.FromArgb(160, 160, 160), False)
    ensure_layer(P.LAYER_GOLD, Color.FromArgb(*P.GOLD[:3]))
    ensure_layer(P.LAYER_CHROME, Color.FromArgb(*P.CHROME[:3]))
    ensure_layer(P.LAYER_COLLAR, Color.FromArgb(*P.COLLAR[:3]))
    ensure_layer(P.LAYER_WOOD, Color.FromArgb(*P.WOOD[:3]))
    ensure_layer(P.LAYER_LENS, Color.FromArgb(*P.LENS[:3]))
    ensure_layer(P.LAYER_SIGHT, Color.FromArgb(*P.WOOD[:3]))
    rs.CurrentLayer(P.LAYER_WOOD)


def main():
    setup_doc()
    rs.EnableRedraw(False)
    try:
        add_brep(cylinder_x(P.EYE_X, P.EYE_L, P.EYE_R), P.LAYER_GOLD, "eyepiece")
        add_brep(cylinder_x(P.SILVER_X, P.SILVER_L, P.SILVER_R), P.LAYER_CHROME, "draw-tube")
        add_brep(
            prism_x(P.COLLAR_X, P.COLLAR_L, P.COLLAR_R, P.COLLAR_SIDES, math.pi / P.COLLAR_SIDES),
            P.LAYER_COLLAR,
            "collar",
        )
        add_brep(frustum_x(P.BARREL_X0, P.BARREL_X1, P.BARREL_R0, P.BARREL_R1), P.LAYER_WOOD, "barrel")
        add_brep(pipe_x(P.RIM_X, P.RIM_L, P.RIM_R_OUT, P.RIM_R_IN), P.LAYER_WOOD, "objective-rim")
        add_brep(pipe_x(P.RING_X, P.RING_L, P.RING_R_OUT, P.RING_R_IN), P.LAYER_GOLD, "lens-ring")
        add_brep(cylinder_x(P.LENS_X, P.LENS_L, P.LENS_R), P.LAYER_LENS, "lens")
        add_brep(
            box_xyz(P.SIGHT_X0, P.SIGHT_X1, P.SIGHT_Y0, P.SIGHT_Y1, P.SIGHT_Z0, P.SIGHT_Z1),
            P.LAYER_SIGHT,
            "sight",
        )
        rs.CurrentLayer(P.LAYER_WOOD)
        sc.doc.Views.Redraw()
        rs.ZoomExtents()
        log("Spyglass built. Apply a wood texture to 04_Wood for grain.")
    finally:
        rs.EnableRedraw(True)
        sc.doc.Views.Redraw()


main()
