"""Geometry helpers for a spyglass along +X."""

from __future__ import annotations

import math

import rhino3dm as r3d


def _along_x(geom, x0: float, length: float):
    """Rotate a World-Z extrusion so it runs along +X, then move to x0."""
    geom.Rotate(-math.pi / 2.0, r3d.Vector3d(0.0, 1.0, 0.0), r3d.Point3d(0.0, 0.0, 0.0))
    # Cylinder extrusions land on the -X side of the origin after this rotation.
    geom.Translate(r3d.Vector3d(x0 + length, 0.0, 0.0))
    return geom


def cylinder_x(x0: float, length: float, radius: float, cap=True):
    circle = r3d.Circle(r3d.Point3d(0.0, 0.0, 0.0), radius)
    cyl = r3d.Cylinder(circle, length)
    ext = r3d.Extrusion.CreateCylinderExtrusion(cyl, cap, cap)
    return _along_x(ext, x0, length) if ext is not None else None


def pipe_x(x0: float, length: float, r_out: float, r_in: float):
    circle = r3d.Circle(r3d.Point3d(0.0, 0.0, 0.0), r_out)
    cyl = r3d.Cylinder(circle, length)
    ext = r3d.Extrusion.CreatePipeExtrusion(cyl, r_in, True, True)
    return _along_x(ext, x0, length) if ext is not None else None


def frustum_x(x0: float, x1: float, r0: float, r1: float):
    profile = r3d.LineCurve(r3d.Point3d(x0, r0, 0.0), r3d.Point3d(x1, r1, 0.0))
    axis = r3d.Line(r3d.Point3d(x0, 0.0, 0.0), r3d.Point3d(x1, 0.0, 0.0))
    rev = r3d.RevSurface.Create(profile, axis, 0.0, 2.0 * math.pi)
    if rev is None:
        return None
    return r3d.Brep.CreateFromRevSurface(rev, True, True)


def prism_x(x0: float, length: float, radius: float, sides: int, rotation=0.0):
    pts = []
    for i in range(sides + 1):
        a = rotation + 2.0 * math.pi * i / sides
        pts.append(r3d.Point3d(radius * math.cos(a), radius * math.sin(a), 0.0))
    ext = r3d.Extrusion.Create(r3d.PolylineCurve(r3d.Polyline(pts)), length, True)
    return _along_x(ext, x0, length) if ext is not None else None


def box_xyz(x0, x1, y0, y1, z0, z1):
    bb = r3d.BoundingBox(r3d.Point3d(x0, y0, z0), r3d.Point3d(x1, y1, z1))
    return r3d.Brep.CreateFromBox(r3d.Box(bb))
