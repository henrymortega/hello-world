#! python 3
"""
Modern robot vacuum for Rhino 8.

ScriptEditor → Open this file → Run
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
    Rhino.RhinoApp.WriteLine("[robot-vacuum] " + str(msg))


def ensure_layer(name, color, visible=True):
    if not rs.IsLayer(name):
        rs.AddLayer(name, color=color)
    rs.LayerVisible(name, visible)


def add_brep(brep, layer, name, color):
    if brep is None:
        return None
    oid = sc.doc.Objects.AddBrep(brep)
    if oid == System.Guid.Empty:
        return None
    rs.ObjectLayer(oid, layer)
    rs.ObjectName(oid, name)
    rs.ObjectColor(oid, color)
    return oid


def cylinder_z(x, y, z0, height, radius):
    plane = rg.Plane(rg.Point3d(x, y, z0), rg.Vector3d.ZAxis)
    cyl = rg.Cylinder(rg.Circle(plane, radius), height)
    ext = rg.Extrusion.CreateCylinderExtrusion(cyl, True, True)
    return ext.ToBrep() if ext else None


def pipe_z(x, y, z0, height, r_out, r_in):
    plane = rg.Plane(rg.Point3d(x, y, z0), rg.Vector3d.ZAxis)
    cyl = rg.Cylinder(rg.Circle(plane, r_out), height)
    ext = rg.Extrusion.CreatePipeExtrusion(cyl, r_in, True, True)
    return ext.ToBrep() if ext else None


def box_xyz(x0, x1, y0, y1, z0, z1):
    return rg.Brep.CreateFromBox(rg.BoundingBox(rg.Point3d(x0, y0, z0), rg.Point3d(x1, y1, z1)))


def revolve_profile(pts_xz):
    pts = System.Collections.Generic.List[rg.Point3d]()
    for x, z in pts_xz:
        pts.Add(rg.Point3d(x, 0, z))
    crv = rg.Curve.CreateControlPointCurve(pts, 3)
    axis = rg.Line(rg.Point3d(0, 0, 0), rg.Point3d(0, 0, 1))
    rev = rg.RevSurface.Create(crv, axis, 0.0, 2.0 * math.pi)
    if rev is None:
        return None
    return rg.Brep.CreateFromRevSurface(rev, True, True)


def torus(major_r, minor_r, z):
    circle = rg.Circle(rg.Point3d(major_r, 0, z), minor_r)
    crv = circle.ToNurbsCurve()
    crv.Rotate(math.pi / 2.0, rg.Vector3d.XAxis, rg.Point3d(major_r, 0, z))
    axis = rg.Line(rg.Point3d(0, 0, 0), rg.Point3d(0, 0, 1))
    rev = rg.RevSurface.Create(crv, axis, 0.0, 2.0 * math.pi)
    if rev is None:
        return None
    return rg.Brep.CreateFromRevSurface(rev, True, True)


def wheel(x, y, z, radius, width):
    plane = rg.Plane(rg.Point3d(x - width * 0.5, y, z), rg.Vector3d.XAxis)
    cyl = rg.Cylinder(rg.Circle(plane, radius), width)
    ext = rg.Extrusion.CreateCylinderExtrusion(cyl, True, True)
    return ext.ToBrep() if ext else None


def arc_bumper(radius, height, z0, thick, start_deg=-95.0, end_deg=95.0):
    n = 28
    a0 = math.radians(start_deg)
    a1 = math.radians(end_deg)
    outer = []
    inner = []
    for i in range(n + 1):
        t = i / float(n)
        a = a0 + (a1 - a0) * t
        outer.append(rg.Point3d(radius * math.cos(a), radius * math.sin(a), z0))
        r_in = radius - thick
        inner.append(rg.Point3d(r_in * math.cos(a), r_in * math.sin(a), z0))
    loop = outer + list(reversed(inner)) + [outer[0]]
    crv = rg.Polyline(loop).ToNurbsCurve()
    ext = rg.Extrusion.Create(crv, height, True)
    return ext.ToBrep() if ext else None


def setup():
    sc.doc.ModelUnitSystem = Rhino.UnitSystem.Millimeters
    ensure_layer(P.LAYER_CONSTRUCTION, Color.FromArgb(160, 160, 160), False)
    ensure_layer(P.LAYER_BODY, Color.FromArgb(*P.WHITE[:3]))
    ensure_layer(P.LAYER_BUMPER, Color.FromArgb(*P.CHARCOAL[:3]))
    ensure_layer(P.LAYER_LIDAR, Color.FromArgb(*P.DARK[:3]))
    ensure_layer(P.LAYER_CONTROLS, Color.FromArgb(*P.ACCENT[:3]))
    ensure_layer(P.LAYER_WHEELS, Color.FromArgb(*P.RUBBER[:3]))
    ensure_layer(P.LAYER_BRUSHES, Color.FromArgb(*P.SMOKE[:3]))
    ensure_layer(P.LAYER_SENSORS, Color.FromArgb(*P.SILVER[:3]))
    rs.CurrentLayer(P.LAYER_BODY)


def main():
    setup()
    rs.EnableRedraw(False)
    try:
        c_white = Color.FromArgb(*P.WHITE[:3])
        c_char = Color.FromArgb(*P.CHARCOAL[:3])
        c_dark = Color.FromArgb(*P.DARK[:3])
        c_led = Color.FromArgb(*P.ACCENT[:3])
        c_rubber = Color.FromArgb(*P.RUBBER[:3])
        c_smoke = Color.FromArgb(*P.SMOKE[:3])
        c_silver = Color.FromArgb(*P.SILVER[:3])

        add_brep(cylinder_z(0, 0, P.BODY_Z0, P.BODY_H, P.BODY_R), P.LAYER_BODY, "body", c_white)
        h0 = P.BODY_Z0 + P.BODY_H
        h1 = h0 + P.TOP_DOME_H
        add_brep(
            revolve_profile([(P.BODY_R - 0.5, h0), (P.BODY_R - 4, h0 + 4), (P.BODY_R * 0.55, h1 - 1.5), (0, h1)]),
            P.LAYER_BODY,
            "top-dome",
            c_white,
        )
        add_brep(
            box_xyz(-P.BIN_W * 0.5, P.BIN_W * 0.5, P.BIN_Y - P.BIN_D, P.BIN_Y, P.BIN_Z, P.BIN_Z + P.BIN_H),
            P.LAYER_BODY,
            "dustbin-lid",
            c_white,
        )
        add_brep(arc_bumper(P.BUMPER_R, P.BUMPER_H, P.BUMPER_Z, P.BUMPER_THICK), P.LAYER_BUMPER, "bumper", c_char)
        add_brep(torus(P.BODY_R - 1.0, 3.5, P.BUMPER_Z + P.BUMPER_H), P.LAYER_BUMPER, "bumper-bead", c_char)

        add_brep(cylinder_z(0, 0, P.LIDAR_Z, P.LIDAR_H, P.LIDAR_R), P.LAYER_LIDAR, "lidar-body", c_dark)
        add_brep(
            pipe_z(0, 0, P.LIDAR_Z + 6, P.LIDAR_WINDOW_H, P.LIDAR_WINDOW_R, P.LIDAR_WINDOW_R_IN),
            P.LAYER_LIDAR,
            "lidar-window",
            c_smoke,
        )
        add_brep(cylinder_z(0, 0, P.LIDAR_Z + P.LIDAR_H - 2, 3, P.LIDAR_CAP_R), P.LAYER_LIDAR, "lidar-cap", c_dark)

        add_brep(cylinder_z(P.BUTTON_X, 0, P.BUTTON_Z, 2.5, P.BUTTON_R), P.LAYER_CONTROLS, "power-button", c_dark)
        add_brep(
            pipe_z(P.BUTTON_X, 0, P.BUTTON_Z + 0.5, 1.5, P.LED_R_OUT, P.LED_R_IN),
            P.LAYER_CONTROLS,
            "status-led",
            c_led,
        )
        add_brep(
            box_xyz(
                -P.SENSOR_W * 0.5,
                P.SENSOR_W * 0.5,
                P.SENSOR_Y - P.SENSOR_D,
                P.SENSOR_Y,
                P.SENSOR_Z,
                P.SENSOR_Z + P.SENSOR_H,
            ),
            P.LAYER_SENSORS,
            "front-sensors",
            c_silver,
        )

        add_brep(wheel(-P.WHEEL_X, 0, P.WHEEL_Z, P.WHEEL_R, P.WHEEL_W), P.LAYER_WHEELS, "wheel-left", c_rubber)
        add_brep(wheel(P.WHEEL_X, 0, P.WHEEL_Z, P.WHEEL_R, P.WHEEL_W), P.LAYER_WHEELS, "wheel-right", c_rubber)
        add_brep(rg.Brep.CreateFromSphere(rg.Sphere(rg.Point3d(0, P.CASTER_Y, P.CASTER_Z), P.CASTER_R)), P.LAYER_WHEELS, "caster", c_rubber)

        add_brep(
            cylinder_z(P.SIDE_BRUSH_X, P.SIDE_BRUSH_Y, P.SIDE_BRUSH_Z, 4, P.SIDE_BRUSH_HUB_R),
            P.LAYER_BRUSHES,
            "side-brush-hub",
            c_dark,
        )
        for i, ang in enumerate((20, 140, 260)):
            a = math.radians(ang)
            x1 = P.SIDE_BRUSH_X + P.SIDE_BRUSH_HUB_R * math.cos(a)
            y1 = P.SIDE_BRUSH_Y + P.SIDE_BRUSH_HUB_R * math.sin(a)
            x2 = P.SIDE_BRUSH_X + P.SIDE_BRUSH_R * math.cos(a)
            y2 = P.SIDE_BRUSH_Y + P.SIDE_BRUSH_R * math.sin(a)
            add_brep(
                box_xyz(min(x1, x2) - 2, max(x1, x2) + 2, min(y1, y2) - 2, max(y1, y2) + 2, P.SIDE_BRUSH_Z, P.SIDE_BRUSH_Z + 3),
                P.LAYER_BRUSHES,
                "side-bristle-{}".format(i),
                c_smoke,
            )
        add_brep(wheel(0, P.ROLLER_Y, P.ROLLER_Z, P.ROLLER_R, P.ROLLER_L), P.LAYER_BRUSHES, "main-roller", c_dark)

        rs.ZoomExtents()
        log("Robot vacuum built (~350 mm diameter).")
    finally:
        rs.EnableRedraw(True)
        sc.doc.Views.Redraw()


main()
