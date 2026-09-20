"""Write tube_field.3dm — hollow green tubes + silk-fold wave surface."""

from __future__ import annotations

from pathlib import Path

import rhino3dm as r3d

import params as P
from field import field_size, iter_tubes, wave_points, wave_shade_rgb

OUT = Path(__file__).resolve().parent / "tube_field.3dm"


def _layer(name, r, g, b, visible=True):
    layer = r3d.Layer()
    layer.Name = name
    layer.Color = (r, g, b, 255)
    layer.Visible = visible
    return layer


def _attr(layer_index, name=None, color=None, material_index=None):
    attr = r3d.ObjectAttributes()
    attr.LayerIndex = layer_index
    if name:
        attr.Name = name
    if color is not None:
        attr.ColorSource = r3d.ObjectColorSource.ColorFromObject
        attr.ObjectColor = color
    if material_index is not None:
        attr.MaterialSource = r3d.ObjectMaterialSource.MaterialFromObject
        attr.MaterialIndex = material_index
    return attr


def add_material(f, name, diffuse, transparency=0.0, ior=1.0):
    mat = r3d.Material()
    mat.Name = name
    mat.DiffuseColor = diffuse
    mat.Transparency = transparency
    mat.IndexOfRefraction = ior
    return f.Materials.Add(mat)


def make_wave_nurbs(grid):
    nu = len(grid)
    nv = len(grid[0])
    srf = r3d.NurbsSurface.Create(3, False, 4, 4, nu, nv)
    srf.KnotsU.CreateUniformKnots(1.0)
    srf.KnotsV.CreateUniformKnots(1.0)
    for i in range(nu):
        for j in range(nv):
            x, y, z = grid[i][j]
            srf.Points[i, j] = r3d.Point4d(x, y, z, 1.0)
    return srf


def make_wave_mesh(grid):
    nu = len(grid)
    nv = len(grid[0])
    mesh = r3d.Mesh()
    for i in range(nu):
        for j in range(nv):
            x, y, z = grid[i][j]
            mesh.Vertices.Add(x, y, z)
            r, g, b = wave_shade_rgb(x, y)
            mesh.VertexColors.Add(r, g, b)
    for i in range(nu - 1):
        for j in range(nv - 1):
            a = i * nv + j
            b = (i + 1) * nv + j
            c = (i + 1) * nv + (j + 1)
            d = i * nv + (j + 1)
            mesh.Faces.AddFace(a, b, c, d)
    mesh.Normals.ComputeNormals()
    mesh.Compact()
    return mesh


def make_ground():
    w, d = field_size()
    pad = 80.0
    pts = [
        r3d.Point3d(-w * 0.5 - pad, -d * 0.5 - pad, -1.0),
        r3d.Point3d(w * 0.5 + P.WAVE_OVERHANG, -d * 0.5 - pad, -1.0),
        r3d.Point3d(w * 0.5 + P.WAVE_OVERHANG, d * 0.5 + pad, -1.0),
        r3d.Point3d(-w * 0.5 - pad, d * 0.5 + pad, -1.0),
        r3d.Point3d(-w * 0.5 - pad, -d * 0.5 - pad, -1.0),
    ]
    return r3d.PolylineCurve(r3d.Polyline(pts))


def main():
    f = r3d.File3dm()
    f.Settings.ModelUnitSystem = r3d.UnitSystem.Millimeters
    f.Settings.ModelAbsoluteTolerance = 0.01

    layers = [
        _layer(P.LAYER_CONSTRUCTION, 160, 160, 160, visible=False),
        _layer(P.LAYER_GROUND, 230, 230, 234),
        _layer(P.LAYER_TUBES, 36, 158, 78),
        _layer(P.LAYER_DOTS, 22, 110, 52),
        _layer(P.LAYER_WAVES, 240, 240, 244, visible=False),
        _layer(P.LAYER_STRIPES, 24, 24, 26, visible=True),
    ]
    for layer in layers:
        f.Layers.Add(layer)
    index = {layer.Name: i for i, layer in enumerate(layers)}

    mat_glass = add_material(f, "green-glass", P.GREEN, transparency=0.55, ior=1.5)
    mat_white = add_material(f, "silk-white", P.WHITE, transparency=0.0, ior=1.0)

    ground = make_ground()
    ground_ext = r3d.Extrusion.Create(ground, 1.0, True)
    if ground_ext is not None:
        f.Objects.AddExtrusion(
            ground_ext,
            _attr(index[P.LAYER_GROUND], "ground", color=P.WHITE, material_index=mat_white),
        )

    n_pipes = n_dots = 0
    for x, y, z, is_dot in iter_tubes():
        if is_dot or z < 4.0:
            r = P.TUBE_OUTER_R * (0.4 if is_dot else 0.7)
            circle = r3d.Circle(r3d.Point3d(x, y, 0.0), r)
            cyl = r3d.Cylinder(circle, max(z, P.DOT_HEIGHT))
            solid = r3d.Extrusion.CreateCylinderExtrusion(cyl, True, True)
            if solid is None:
                continue
            f.Objects.AddExtrusion(
                solid,
                _attr(index[P.LAYER_DOTS], "dot", color=P.GREEN_DARK, material_index=mat_glass),
            )
            n_dots += 1
            continue

        circle = r3d.Circle(r3d.Point3d(x, y, 0.0), P.TUBE_OUTER_R)
        cyl = r3d.Cylinder(circle, z)
        pipe = r3d.Extrusion.CreatePipeExtrusion(cyl, P.TUBE_INNER_R, True, True)
        if pipe is None:
            pipe = r3d.Extrusion.CreateCylinderExtrusion(cyl, True, True)
        if pipe is None:
            continue
        f.Objects.AddExtrusion(
            pipe,
            _attr(index[P.LAYER_TUBES], "tube", color=P.GREEN, material_index=mat_glass),
        )
        n_pipes += 1

    grid = wave_points(36, 30)
    srf = make_wave_nurbs(grid)
    if srf and srf.IsValid:
        brep = r3d.Brep.CreateFromSurface(srf)
        if brep is not None:
            f.Objects.AddBrep(
                brep,
                _attr(index[P.LAYER_WAVES], "wave-surface", color=P.WHITE, material_index=mat_white),
            )
    mesh = make_wave_mesh(grid)
    f.Objects.AddMesh(mesh, _attr(index[P.LAYER_STRIPES], "wave-shading"))

    note = "Tube field (mm)\nHollow tubes: {}   Fade dots: {}\nRun tube_field.py in Rhino 8 to rebuild.\nZebra analysis on the wave surface matches the silk folds.".format(
        n_pipes, n_dots
    )
    w, d = field_size()
    f.Objects.AddTextDot(note, r3d.Point3d(0.0, -d * 0.5 - 60.0, 0.0))

    f.Write(str(OUT), 8)
    print("wrote {}  pipes={} dots={}".format(OUT, n_pipes, n_dots))


if __name__ == "__main__":
    main()
