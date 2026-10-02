"""Geometry helpers for building footwear solids with rhino3dm."""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

import rhino3dm as r3d

Point = r3d.Point3d


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def smoothstep(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def pt(x: float, y: float, z: float) -> Point:
    return r3d.Point3d(x, y, z)


def circle_pts(
    center: Point,
    radius: float,
    normal: r3d.Vector3d,
    count: int = 24,
) -> List[Point]:
    """Points around a circle in a plane with given normal."""
    n = r3d.Vector3d(normal.X, normal.Y, normal.Z)
    n.Unitize()
    # Build orthonormal basis
    helper = r3d.Vector3d(0, 0, 1) if abs(n.Z) < 0.9 else r3d.Vector3d(0, 1, 0)
    u = r3d.Vector3d.CrossProduct(n, helper)
    u.Unitize()
    v = r3d.Vector3d.CrossProduct(n, u)
    v.Unitize()
    pts = []
    for i in range(count):
        a = 2.0 * math.pi * i / count
        pts.append(
            pt(
                center.X + radius * (math.cos(a) * u.X + math.sin(a) * v.X),
                center.Y + radius * (math.cos(a) * u.Y + math.sin(a) * v.Y),
                center.Z + radius * (math.cos(a) * u.Z + math.sin(a) * v.Z),
            )
        )
    return pts


def ellipse_xy(cx: float, cy: float, z: float, rx: float, ry: float, count: int = 32) -> List[Point]:
    pts = []
    for i in range(count):
        a = 2.0 * math.pi * i / count
        pts.append(pt(cx + rx * math.cos(a), cy + ry * math.sin(a), z))
    return pts


def ellipse_xz(cx: float, cz: float, y: float, rx: float, rz: float, count: int = 32) -> List[Point]:
    pts = []
    for i in range(count):
        a = 2.0 * math.pi * i / count
        pts.append(pt(cx + rx * math.cos(a), y, cz + rz * math.sin(a)))
    return pts


def footprint_section(
    x: float,
    half_width: float,
    z: float,
    toe_bias: float = 0.0,
    count: int = 36,
) -> List[Point]:
    """Closed oval footprint section at X, centered on Y=0, on plane Z=z.

    The Air Max 1 last is slightly asymmetrical (lateral flare), approximated
    with a mild lateral bias when toe_bias != 0.
    """
    pts = []
    for i in range(count):
        a = 2.0 * math.pi * i / count
        # Squeeze aft, round fore — handled by caller via half_width
        # Mild lateral offset toward +Y (lateral on left shoe)
        oy = toe_bias * math.sin(a) * 0.15 if math.sin(a) > 0 else 0.0
        pts.append(pt(x, half_width * math.sin(a) + oy, z))
    return pts


def last_section(
    x: float,
    half_width: float,
    z_bottom: float,
    height: float,
    crown: float = 0.55,
    count: int = 40,
) -> List[Point]:
    """Upper last cross-section in YZ at X.

    Starts at medial sole edge, goes up around the vamp/collar and back.
    Closed loop approximating a footwear last slice.
    """
    pts: List[Point] = []
    # Parametrize 0..1 around the section: sole -> lateral -> top -> medial
    for i in range(count):
        t = i / count
        ang = 2.0 * math.pi * t
        # Base ellipse then raise the top
        y = half_width * math.sin(ang)
        # Bottom half stays near sole; top half rises
        if math.cos(ang) <= 0:
            # upper half (cos negative if we use sin for Y and cos for Z from bottom)
            z = z_bottom + height * ((-math.cos(ang)) ** crown)
            # Narrow slightly toward topline
            y *= lerp(1.0, 0.82, (-math.cos(ang)))
        else:
            z = z_bottom
            # Flat-ish sole with slight camber
            z += 0.6 * (1.0 - abs(math.sin(ang)))
        pts.append(pt(x, y, z))
    return pts


def curve_from_pts(points: Sequence[Point], degree: int = 3) -> r3d.NurbsCurve:
    return r3d.NurbsCurve.CreateControlPointCurve(list(points), degree)


def closed_polyline(points: Sequence[Point]) -> r3d.PolylineCurve:
    pl = r3d.Polyline(list(points) + [points[0]])
    return r3d.PolylineCurve(pl)


def loft_mesh(sections: Sequence[Sequence[Point]], cap: bool = True) -> r3d.Mesh:
    """Loft a mesh through closed sections with identical point counts."""
    if len(sections) < 2:
        raise ValueError("Need at least two sections")
    n = len(sections[0])
    for s in sections:
        if len(s) != n:
            raise ValueError("All sections must have the same point count")

    mesh = r3d.Mesh()
    # Vertices
    for sec in sections:
        for p in sec:
            mesh.Vertices.Add(p.X, p.Y, p.Z)

    rows = len(sections)
    # Side faces
    for r in range(rows - 1):
        for i in range(n):
            i0 = r * n + i
            i1 = r * n + ((i + 1) % n)
            i2 = (r + 1) * n + ((i + 1) % n)
            i3 = (r + 1) * n + i
            mesh.Faces.AddFace(i0, i1, i2, i3)

    if cap:
        # Fan-cap start and end using centroid vertices
        def add_cap(row: int, flip: bool) -> None:
            cx = cy = cz = 0.0
            for i in range(n):
                p = sections[row][i]
                cx += p.X
                cy += p.Y
                cz += p.Z
            cx /= n
            cy /= n
            cz /= n
            cidx = len(mesh.Vertices)
            mesh.Vertices.Add(cx, cy, cz)
            base = row * n
            for i in range(n):
                a = base + i
                b = base + ((i + 1) % n)
                if flip:
                    mesh.Faces.AddFace(cidx, b, a)
                else:
                    mesh.Faces.AddFace(cidx, a, b)

        add_cap(0, flip=True)
        add_cap(rows - 1, flip=False)

    mesh.Normals.ComputeNormals()
    mesh.Compact()
    return mesh


def box_mesh(x0, y0, z0, x1, y1, z1) -> r3d.Mesh:
    """Axis-aligned box as a mesh."""
    # Normalize
    xa, xb = sorted((x0, x1))
    ya, yb = sorted((y0, y1))
    za, zb = sorted((z0, z1))
    corners = [
        (xa, ya, za),
        (xb, ya, za),
        (xb, yb, za),
        (xa, yb, za),
        (xa, ya, zb),
        (xb, ya, zb),
        (xb, yb, zb),
        (xa, yb, zb),
    ]
    mesh = r3d.Mesh()
    for c in corners:
        mesh.Vertices.Add(*c)
    faces = [
        (0, 1, 2, 3),  # bottom
        (4, 7, 6, 5),  # top
        (0, 4, 5, 1),  # front
        (1, 5, 6, 2),  # right
        (2, 6, 7, 3),  # back
        (3, 7, 4, 0),  # left
    ]
    for f in faces:
        mesh.Faces.AddFace(*f)
    mesh.Normals.ComputeNormals()
    mesh.Compact()
    return mesh


def _vlen(v: r3d.Vector3d) -> float:
    return math.sqrt(v.X * v.X + v.Y * v.Y + v.Z * v.Z)


def cylinder_mesh(
    start: Point,
    end: Point,
    radius: float,
    sides: int = 16,
) -> r3d.Mesh:
    """Simple capped cylinder mesh between two points."""
    axis = r3d.Vector3d(end.X - start.X, end.Y - start.Y, end.Z - start.Z)
    length = _vlen(axis)
    if length < 1e-9:
        return r3d.Mesh()
    axis.Unitize()
    # Basis
    helper = r3d.Vector3d(0, 0, 1) if abs(axis.Z) < 0.9 else r3d.Vector3d(0, 1, 0)
    u = r3d.Vector3d.CrossProduct(axis, helper)
    u.Unitize()
    v = r3d.Vector3d.CrossProduct(axis, u)
    v.Unitize()

    mesh = r3d.Mesh()
    for end_pt in (start, end):
        for i in range(sides):
            a = 2.0 * math.pi * i / sides
            mesh.Vertices.Add(
                end_pt.X + radius * (math.cos(a) * u.X + math.sin(a) * v.X),
                end_pt.Y + radius * (math.cos(a) * u.Y + math.sin(a) * v.Y),
                end_pt.Z + radius * (math.cos(a) * u.Z + math.sin(a) * v.Z),
            )
    for i in range(sides):
        i0 = i
        i1 = (i + 1) % sides
        i2 = sides + ((i + 1) % sides)
        i3 = sides + i
        mesh.Faces.AddFace(i0, i1, i2, i3)
    # Caps
    c0 = len(mesh.Vertices)
    mesh.Vertices.Add(start.X, start.Y, start.Z)
    for i in range(sides):
        mesh.Faces.AddFace(c0, (i + 1) % sides, i)
    c1 = len(mesh.Vertices)
    mesh.Vertices.Add(end.X, end.Y, end.Z)
    for i in range(sides):
        mesh.Faces.AddFace(c1, sides + i, sides + ((i + 1) % sides))
    mesh.Normals.ComputeNormals()
    mesh.Compact()
    return mesh


def pipe_along_polyline(points: Sequence[Point], radius: float, sides: int = 10) -> r3d.Mesh:
    """Approximate a pipe by lofting circular sections along a polyline."""
    sections = []
    for i, p in enumerate(points):
        if i == 0:
            d = r3d.Vector3d(points[1].X - p.X, points[1].Y - p.Y, points[1].Z - p.Z)
        elif i == len(points) - 1:
            d = r3d.Vector3d(p.X - points[i - 1].X, p.Y - points[i - 1].Y, p.Z - points[i - 1].Z)
        else:
            d = r3d.Vector3d(
                points[i + 1].X - points[i - 1].X,
                points[i + 1].Y - points[i - 1].Y,
                points[i + 1].Z - points[i - 1].Z,
            )
        if _vlen(d) < 1e-9:
            d = r3d.Vector3d(1, 0, 0)
        d.Unitize()
        sections.append(circle_pts(p, radius, d, sides))
    return loft_mesh(sections, cap=True)


def ruled_brep(curve_a: r3d.Curve, curve_b: r3d.Curve) -> r3d.Brep | None:
    srf = r3d.NurbsSurface.CreateRuledSurface(curve_a, curve_b)
    if srf is None:
        return None
    return r3d.Brep.CreateFromSurface(srf)


def transform_mesh(mesh: r3d.Mesh, xform: r3d.Transform) -> r3d.Mesh:
    m = mesh.Duplicate()
    m.Transform(xform)
    return m


def mirror_y(mesh: r3d.Mesh) -> r3d.Mesh:
    xform = r3d.Transform.Mirror(r3d.Plane.WorldZX)
    return transform_mesh(mesh, xform)


def offset_points(points: Sequence[Point], dx=0.0, dy=0.0, dz=0.0) -> List[Point]:
    return [pt(p.X + dx, p.Y + dy, p.Z + dz) for p in points]


def scale_section_yz(points: Sequence[Point], sy: float, sz: float, z0: float) -> List[Point]:
    out = []
    for p in points:
        out.append(pt(p.X, p.Y * sy, z0 + (p.Z - z0) * sz))
    return out
