"""Geometry helpers for a Z-up robot vacuum."""

from __future__ import annotations

import math

import rhino3dm as r3d


def cylinder_z(x: float, y: float, z0: float, height: float, radius: float, cap=True):
    circle = r3d.Circle(r3d.Point3d(x, y, z0), radius)
    cyl = r3d.Cylinder(circle, height)
    return r3d.Extrusion.CreateCylinderExtrusion(cyl, cap, cap)


def pipe_z(x: float, y: float, z0: float, height: float, r_out: float, r_in: float):
    circle = r3d.Circle(r3d.Point3d(x, y, z0), r_out)
    cyl = r3d.Cylinder(circle, height)
    return r3d.Extrusion.CreatePipeExtrusion(cyl, r_in, True, True)


def box(x0, x1, y0, y1, z0, z1):
    bb = r3d.BoundingBox(r3d.Point3d(x0, y0, z0), r3d.Point3d(x1, y1, z1))
    return r3d.Brep.CreateFromBox(r3d.Box(bb))


def sphere(x, y, z, radius):
    return r3d.Sphere(r3d.Point3d(x, y, z), radius)


def revolve_profile(pts_xz, z_axis=True):
    """Revolve an XZ (or XY) profile around the world Z axis into a solid-ish brep."""
    crv = r3d.Curve.CreateControlPointCurve([r3d.Point3d(x, 0.0, z) for x, z in pts_xz], 3)
    if crv is None:
        return None
    axis = r3d.Line(r3d.Point3d(0.0, 0.0, 0.0), r3d.Point3d(0.0, 0.0, 1.0))
    rev = r3d.RevSurface.Create(crv, axis, 0.0, 2.0 * math.pi)
    if rev is None:
        return None
    return r3d.Brep.CreateFromRevSurface(rev, True, True)


def torus(major_r: float, minor_r: float, z: float):
    circle = r3d.Circle(r3d.Point3d(major_r, 0.0, z), minor_r)
    crv = circle.ToNurbsCurve()
    crv.Rotate(math.pi / 2.0, r3d.Vector3d(1.0, 0.0, 0.0), r3d.Point3d(major_r, 0.0, z))
    axis = r3d.Line(r3d.Point3d(0.0, 0.0, 0.0), r3d.Point3d(0.0, 0.0, 1.0))
    rev = r3d.RevSurface.Create(crv, axis, 0.0, 2.0 * math.pi)
    if rev is None:
        return None
    return r3d.Brep.CreateFromRevSurface(rev, True, True)


def cylinder_along_x(x0: float, y: float, z: float, length: float, radius: float):
    """Cylinder whose axis runs along +X."""
    circle = r3d.Circle(r3d.Point3d(0.0, y, z), radius)
    cyl = r3d.Cylinder(circle, length)
    ext = r3d.Extrusion.CreateCylinderExtrusion(cyl, True, True)
    if ext is None:
        return None
    # Extrusion is along +Z from (0,y,z); rotate to +X and place
    ext.Rotate(-math.pi / 2.0, r3d.Vector3d(0.0, 1.0, 0.0), r3d.Point3d(0.0, y, z))
    ext.Translate(r3d.Vector3d(x0 + length, 0.0, 0.0))
    # After rotate around Y through (0,y,z), Z-axis cylinder becomes X-axis.
    # Re-check placement with a cleaner approach:
    return ext


def wheel(x: float, y: float, z: float, radius: float, width: float, left: bool):
    """Drive wheel as a short cylinder along X (axle)."""
    # Build in local Z then rotate to X
    circle = r3d.Circle(r3d.Point3d(0.0, 0.0, 0.0), radius)
    cyl = r3d.Cylinder(circle, width)
    ext = r3d.Extrusion.CreateCylinderExtrusion(cyl, True, True)
    if ext is None:
        return None
    ext.Rotate(-math.pi / 2.0, r3d.Vector3d(0.0, 1.0, 0.0), r3d.Point3d(0.0, 0.0, 0.0))
    # Now spans roughly -width..0 or 0..width on X depending on rotation — shift so centre is at x
    bb = ext.GetBoundingBox()
    cx = 0.5 * (bb.Min.X + bb.Max.X)
    cy = 0.5 * (bb.Min.Y + bb.Max.Y)
    cz = 0.5 * (bb.Min.Z + bb.Max.Z)
    ext.Translate(r3d.Vector3d(x - cx, y - cy, z - cz))
    return ext


def arc_bumper(radius: float, height: float, z0: float, thick: float, start_deg=-95.0, end_deg=95.0):
    """Front bumper as a thick partial pipe extruded vertically — approximated with a revolved tube segment via mesh of boxes... 

    Use an annular sector: outer arc + inner arc extruded.
    """
    # Outer and inner polylines for a 180° ring segment
    n = 28
    a0 = math.radians(start_deg)
    a1 = math.radians(end_deg)
    outer = []
    inner = []
    for i in range(n + 1):
        t = i / n
        a = a0 + (a1 - a0) * t
        outer.append(r3d.Point3d(radius * math.cos(a), radius * math.sin(a), z0))
        r_in = radius - thick
        inner.append(r3d.Point3d(r_in * math.cos(a), r_in * math.sin(a), z0))
    # closed loop: outer forward + inner reverse
    loop = outer + list(reversed(inner)) + [outer[0]]
    crv = r3d.PolylineCurve(r3d.Polyline(loop))
    return r3d.Extrusion.Create(crv, height, True)
