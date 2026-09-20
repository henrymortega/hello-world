#! python 3
"""
Scale-lattice pendant for Rhino 8.

Builds a rounded-square metal plate with a brick-pattern teardrop lattice
that fades into a solid band at the bottom, plus a spherical hanger.

Run in Rhino:
  ScriptEditor → Open this file → Run
  or  _-RunPythonScript and pick this file

Requires Rhino 8 (CPython 3). Millimeters.
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
from lattice import iter_holes, superellipse_points
from outline import rounded_rect_points


def log(msg):
    Rhino.RhinoApp.WriteLine("[scale-pendant] " + str(msg))


def ensure_layer(name, color, visible=True):
    if not rs.IsLayer(name):
        rs.AddLayer(name, color=color)
    rs.LayerVisible(name, visible)
    return name


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


def add_curve(crv, layer, name=None):
    oid = sc.doc.Objects.AddCurve(crv)
    if oid == System.Guid.Empty:
        return None
    rs.ObjectLayer(oid, layer)
    if name:
        rs.ObjectName(oid, name)
    return oid


def largest_brep(breps):
    if not breps:
        return None
    scored = []
    for b in breps:
        try:
            scored.append((abs(b.GetVolume()), b))
        except Exception:
            bb = b.GetBoundingBox(True)
            scored.append((bb.Volume, b))
    scored.sort(key=lambda t: t[0], reverse=True)
    return scored[0][1]


def boolean_difference(body, cutters, label):
    if not cutters:
        return body
    tol = max(sc.doc.ModelAbsoluteTolerance, 0.01)

    result = rg.Brep.CreateBooleanDifference([body], cutters, tol)
    if result:
        log("{}: batch difference ok ({} cutters → {} pieces)".format(label, len(cutters), len(result)))
        return largest_brep(result)

    log("{}: full batch failed, cutting in chunks of 25".format(label))
    current = body
    chunk = 25
    for start in range(0, len(cutters), chunk):
        group = cutters[start : start + chunk]
        nxt = rg.Brep.CreateBooleanDifference([current], group, tol)
        if nxt:
            current = largest_brep(nxt)
            continue
        for i, cutter in enumerate(group):
            nxt = rg.Brep.CreateBooleanDifference([current], [cutter], tol)
            if nxt:
                current = largest_brep(nxt)
            elif (start + i) % 20 == 0:
                log("{}: skipped cutter {}".format(label, start + i))
    log("{}: finished {} cutters".format(label, len(cutters)))
    return current


def boolean_union(breps):
    tol = max(sc.doc.ModelAbsoluteTolerance, 0.01)
    result = rg.Brep.CreateBooleanUnion(list(breps), tol)
    if result:
        return largest_brep(result)
    current = breps[0]
    for extra in breps[1:]:
        nxt = rg.Brep.CreateBooleanUnion([current, extra], tol)
        if nxt:
            current = largest_brep(nxt)
    return current


def outline_curve():
    pts = [rg.Point3d(x, y, 0.0) for x, y in rounded_rect_points(P.WIDTH, P.HEIGHT, P.CORNER_RADIUS, 16)]
    pts.append(pts[0])
    crv = rg.Curve.CreateControlPointCurve(pts, 3)
    if crv and crv.IsValid:
        if not crv.IsClosed:
            crv.MakeClosed(0.01)
        return crv
    pl = rg.Polyline(pts)
    return pl.ToNurbsCurve()


def hole_curve(cx, cy, rx, ry, z=0.0):
    samples = superellipse_points(cx, cy, rx, ry, P.SUPERELLIPSE_N, 72)
    pts = [rg.Point3d(x, y, z) for x, y in samples]
    pts.append(pts[0])
    crv = rg.NurbsCurve.Create(True, 3, pts)
    if crv is None or not crv.IsValid:
        crv = rg.Curve.CreateControlPointCurve(pts, 3)
    if crv and not crv.IsClosed:
        crv.MakeClosed(0.01)
    return crv


def capped_extrusion(crv, height):
    ext = rg.Extrusion.Create(crv, height, True)
    if ext is None:
        return None
    return ext.ToBrep()


def build_body():
    crv = outline_curve()
    add_curve(crv.DuplicateCurve(), P.LAYER_CONSTRUCTION, "outline")
    body = capped_extrusion(crv, P.THICKNESS)
    if body is None:
        raise RuntimeError("Failed to extrude the pendant body")
    return body


def build_cutters():
    through = []
    pockets = []
    z_lo, z_hi = -2.0, P.THICKNESS + 2.0
    for cx, cy, rx, ry, scale in iter_holes(min_scale=0.08):
        crv = hole_curve(cx, cy, rx, ry, 0.0)
        add_curve(crv.DuplicateCurve(), P.LAYER_CONSTRUCTION, "cell")
        height_norm = (cy + P.HEIGHT * 0.5) / P.HEIGHT
        if height_norm >= P.BLIND_POCKET_BELOW and scale >= 0.35:
            solid = capped_extrusion(crv, z_hi - z_lo)
            if solid:
                solid.Translate(rg.Vector3d(0, 0, z_lo))
                through.append(solid)
        else:
            depth = max(1.2, P.THICKNESS * 0.65 * scale)
            crv_front = hole_curve(cx, cy, rx, ry, P.THICKNESS + 0.2)
            solid = capped_extrusion(crv_front, -(depth + 0.2))
            if solid:
                pockets.append(solid)
    return through, pockets


def build_hardware():
    center = rg.Point3d(0.0, P.HEIGHT * 0.5, P.THICKNESS * 0.5)
    sphere = rg.Brep.CreateFromSphere(rg.Sphere(center, P.HANGER_SPHERE_R))
    plane = rg.Plane(center, rg.Vector3d.YAxis)
    circle = rg.Circle(plane, P.STEM_R)
    cyl = rg.Cylinder(circle, P.STEM_H).ToBrep(True, True)
    return sphere, cyl


def setup_doc():
    sc.doc.ModelUnitSystem = Rhino.UnitSystem.Millimeters
    ensure_layer(P.LAYER_CONSTRUCTION, Color.FromArgb(160, 160, 160), visible=False)
    ensure_layer(P.LAYER_BODY, Color.FromArgb(196, 196, 204), visible=True)
    ensure_layer(P.LAYER_LATTICE, Color.FromArgb(120, 120, 128), visible=True)
    ensure_layer(P.LAYER_POCKETS, Color.FromArgb(90, 90, 96), visible=True)
    ensure_layer(P.LAYER_HARDWARE, Color.FromArgb(210, 210, 220), visible=True)
    rs.CurrentLayer(P.LAYER_BODY)


def main():
    setup_doc()
    rs.EnableRedraw(False)
    try:
        log("Building rounded-square body {} x {} x {} mm".format(P.WIDTH, P.HEIGHT, P.THICKNESS))
        body = build_body()
        through, pockets = build_cutters()
        log("Cutters: {} through-holes, {} fade pockets".format(len(through), len(pockets)))

        body = boolean_difference(body, through, "through-holes")
        body = boolean_difference(body, pockets, "pockets")

        sphere, stem = build_hardware()
        united = boolean_union([body, sphere, stem])
        if united:
            body = united

        oid = add_brep(body, P.LAYER_BODY, "scale-pendant")
        if oid is None:
            raise RuntimeError("Could not add the finished pendant to the document")

        rs.CurrentLayer(P.LAYER_BODY)
        sc.doc.Views.Redraw()
        rs.ZoomExtents()
        log("Done. Pendant is on layer '{}'.".format(P.LAYER_BODY))
        log("Construction curves are on hidden layer '{}'.".format(P.LAYER_CONSTRUCTION))
        log("Optional: select the pendant and run FilletEdge with radius {} mm.".format(P.HOLE_FILLET))
    finally:
        rs.EnableRedraw(True)
        sc.doc.Views.Redraw()


main()
