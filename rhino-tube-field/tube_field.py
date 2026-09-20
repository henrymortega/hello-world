#! python 3
"""
Green tube-field dissolving into silk-fold waves.

Run in Rhino 8:
  ScriptEditor → Open this file → Run
  or  _-RunPythonScript and pick this file

After it builds, select the wave surface and run _Zebra for the
black/white fold look from the reference.
"""

from __future__ import annotations

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
from field import field_size, iter_tubes, wave_points


def log(msg):
    Rhino.RhinoApp.WriteLine("[tube-field] " + str(msg))


def ensure_layer(name, color, visible=True):
    if not rs.IsLayer(name):
        rs.AddLayer(name, color=color)
    rs.LayerVisible(name, visible)
    return name


def setup_doc():
    sc.doc.ModelUnitSystem = Rhino.UnitSystem.Millimeters
    ensure_layer(P.LAYER_CONSTRUCTION, Color.FromArgb(160, 160, 160), False)
    ensure_layer(P.LAYER_GROUND, Color.FromArgb(230, 230, 234), True)
    ensure_layer(P.LAYER_TUBES, Color.FromArgb(36, 158, 78), True)
    ensure_layer(P.LAYER_DOTS, Color.FromArgb(22, 110, 52), True)
    ensure_layer(P.LAYER_WAVES, Color.FromArgb(240, 240, 244), True)
    ensure_layer(P.LAYER_STRIPES, Color.FromArgb(30, 30, 32), False)
    rs.CurrentLayer(P.LAYER_TUBES)


def add_brep(brep, layer, name=None):
    if brep is None:
        return None
    oid = sc.doc.Objects.AddBrep(brep)
    if oid == System.Guid.Empty:
        return None
    rs.ObjectLayer(oid, layer)
    if name:
        rs.ObjectName(oid, name)
    return oid


def pipe_brep(x, y, height, r_out, r_in):
    plane = rg.Plane(rg.Point3d(x, y, 0.0), rg.Vector3d.ZAxis)
    circle = rg.Circle(plane, r_out)
    cyl = rg.Cylinder(circle, height)
    ext = rg.Extrusion.CreatePipeExtrusion(cyl, r_in, True, True)
    if ext is not None:
        return ext.ToBrep()
    ext = rg.Extrusion.CreateCylinderExtrusion(cyl, True, True)
    return ext.ToBrep() if ext else None


def cylinder_brep(x, y, height, radius):
    plane = rg.Plane(rg.Point3d(x, y, 0.0), rg.Vector3d.ZAxis)
    circle = rg.Circle(plane, radius)
    cyl = rg.Cylinder(circle, height)
    ext = rg.Extrusion.CreateCylinderExtrusion(cyl, True, True)
    return ext.ToBrep() if ext else None


def build_tubes():
    n_pipes = n_dots = 0
    for x, y, z, is_dot in iter_tubes():
        if is_dot or z < 4.0:
            r = P.TUBE_OUTER_R * (0.4 if is_dot else 0.7)
            brep = cylinder_brep(x, y, max(z, P.DOT_HEIGHT), r)
            add_brep(brep, P.LAYER_DOTS, "dot")
            n_dots += 1
        else:
            brep = pipe_brep(x, y, z, P.TUBE_OUTER_R, P.TUBE_INNER_R)
            add_brep(brep, P.LAYER_TUBES, "tube")
            n_pipes += 1
    return n_pipes, n_dots


def build_wave():
    grid = wave_points(36, 30)
    nu = len(grid)
    nv = len(grid[0])
    pts = System.Collections.Generic.List[rg.Point3d]()
    for i in range(nu):
        for j in range(nv):
            x, y, z = grid[i][j]
            pts.Add(rg.Point3d(x, y, z))
    srf = rg.NurbsSurface.CreateThroughPoints(pts, nu, nv, 3, 3, False, False)
    if srf is None:
        srf = rg.NurbsSurface.CreateThroughPoints(pts, nv, nu, 3, 3, False, False)
    if srf is None:
        log("CreateThroughPoints failed, building from control points")
        srf = rg.NurbsSurface.Create(3, False, 4, 4, nu, nv)
        srf.KnotsU.CreateUniformKnots(1.0)
        srf.KnotsV.CreateUniformKnots(1.0)
        for i in range(nu):
            for j in range(nv):
                x, y, z = grid[i][j]
                srf.Points.SetControlPoint(i, j, rg.ControlPoint(rg.Point3d(x, y, z)))
    brep = rg.Brep.CreateFromSurface(srf)
    return add_brep(brep, P.LAYER_WAVES, "wave-surface")


def build_ground():
    w, d = field_size()
    pad = 80.0
    corners = [
        rg.Point3d(-w * 0.5 - pad, -d * 0.5 - pad, -1.0),
        rg.Point3d(w * 0.5 + P.WAVE_OVERHANG, -d * 0.5 - pad, -1.0),
        rg.Point3d(w * 0.5 + P.WAVE_OVERHANG, d * 0.5 + pad, -1.0),
        rg.Point3d(-w * 0.5 - pad, d * 0.5 + pad, -1.0),
        rg.Point3d(-w * 0.5 - pad, -d * 0.5 - pad, -1.0),
    ]
    crv = rg.Polyline(corners).ToNurbsCurve()
    ext = rg.Extrusion.Create(crv, 1.0, True)
    if ext:
        add_brep(ext.ToBrep(), P.LAYER_GROUND, "ground")


def main():
    setup_doc()
    rs.EnableRedraw(False)
    try:
        log("Building tube field...")
        build_ground()
        n_pipes, n_dots = build_tubes()
        log("Tubes: {} pipes, {} fade dots".format(n_pipes, n_dots))
        oid = build_wave()
        log("Wave surface: {}".format("ok" if oid else "failed"))
        rs.CurrentLayer(P.LAYER_TUBES)
        sc.doc.Views.Redraw()
        rs.ZoomExtents()
        log("Done. Select the wave and run _Zebra for the silk-fold stripes.")
    finally:
        rs.EnableRedraw(True)
        sc.doc.Views.Redraw()


main()
