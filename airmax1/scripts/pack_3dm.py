#!/usr/bin/env python3
"""Pack Blender-exported OBJ parts into a componentized Rhino .3dm for V-Ray."""

from __future__ import annotations

from pathlib import Path

import rhino3dm as r3d

PARTS = Path("/workspace/airmax1/output/blender_parts")
OUT = Path("/workspace/airmax1/output/Nike_AirMax1_US9_Left.3dm")

# name prefix -> (layer, material_name, rgb, mat_kwargs)
LAYER_MAP = {
    "Outsole_Base": ("01_Sole::Outsole", "MAT_Rubber", (18, 18, 18), {"roughness": 0.7}),
    "Waffle_": ("01_Sole::Waffle", "MAT_Rubber", (18, 18, 18), {"roughness": 0.72}),
    "Midsole_Foam": ("02_Midsole::Body", "MAT_Foam", (245, 245, 242), {"roughness": 0.8}),
    "AirUnit_Window": ("03_AirUnit::Window", "MAT_AirClear", (200, 225, 240), {"transparency": 0.75, "ior": 1.49, "roughness": 0.05}),
    "AirUnit_Membrane": ("03_AirUnit::Membrane", "MAT_AirMem", (190, 210, 225), {"transparency": 0.4, "roughness": 0.25}),
    "AirUnit_Pillar": ("03_AirUnit::Pillars", "MAT_AirPillar", (180, 200, 215), {"transparency": 0.3, "roughness": 0.2}),
    "Upper_Mesh_Last": ("04_Upper::MeshBase", "MAT_Mesh", (248, 248, 246), {"roughness": 0.85}),
    "Mudguard_": ("05_Overlays::Mudguard", "MAT_LeatherBlk", (20, 20, 20), {"roughness": 0.42}),
    "Quarter_Suede_": ("05_Overlays::SuedeQuarter", "MAT_Suede", (206, 200, 188), {"roughness": 0.92}),
    "HeelCounter_": ("05_Overlays::HeelCounter", "MAT_Suede", (206, 200, 188), {"roughness": 0.92}),
    "Swoosh_": ("05_Overlays::Swoosh", "MAT_Swoosh", (12, 12, 12), {"roughness": 0.38}),
    "Collar_": ("04_Upper::Collar", "MAT_Collar", (240, 240, 238), {"roughness": 0.8}),
    "Tongue": ("07_SoftGoods::Tongue", "MAT_Tongue", (250, 250, 248), {"roughness": 0.8}),
    "Lace_": ("07_SoftGoods::Laces", "MAT_Lace", (245, 245, 243), {"roughness": 0.7}),
    "Eyelet_": ("06_Hardware::Eyelets", "MAT_Plastic", (25, 25, 25), {"roughness": 0.3}),
    "LaceLock_": ("06_Hardware::LaceLock", "MAT_Plastic", (20, 20, 20), {"roughness": 0.28}),
    "Insole": ("07_SoftGoods::Insole", "MAT_Insole", (235, 232, 225), {"roughness": 0.8}),
}

PARENTS = [
    ("01_Sole", (30, 30, 30)),
    ("02_Midsole", (230, 230, 230)),
    ("03_AirUnit", (180, 220, 255)),
    ("04_Upper", (245, 245, 245)),
    ("05_Overlays", (180, 170, 160)),
    ("06_Hardware", (20, 20, 20)),
    ("07_SoftGoods", (250, 250, 250)),
]


def match_rule(name: str):
    for prefix, rule in LAYER_MAP.items():
        if name == prefix or name.startswith(prefix):
            return rule
    return ("04_Upper::Misc", "MAT_Mesh", (200, 200, 200), {"roughness": 0.5})


def parse_obj(path: Path):
    verts = []
    faces = []
    with path.open() as f:
        for line in f:
            if line.startswith("v "):
                _, x, y, z = line.split()[:4]
                verts.append((float(x), float(y), float(z)))
            elif line.startswith("f "):
                idx = []
                for part in line.split()[1:]:
                    idx.append(int(part.split("/")[0]) - 1)
                if len(idx) >= 3:
                    faces.append(idx)
    return verts, faces


def main():
    doc = r3d.File3dm()
    doc.Settings.ModelUnitSystem = r3d.UnitSystem.Millimeters
    doc.ApplicationName = "AirMax1 Blender Pipeline"
    doc.StartSectionComments = (
        "Nike Air Max 1 US9 Left — organic subdivided mesh from Blender, "
        "componentized for V-Ray. Proportions from Nike FZ5808-102 photography."
    )

    layers = {}
    mats = {}

    def ensure_layer(name, rgb, parent=None):
        if name in layers:
            return layers[name]
        layer = r3d.Layer()
        layer.Name = name
        layer.Color = (*rgb, 255)
        if parent and parent in layers:
            layer.ParentLayerId = doc.Layers[layers[parent]].Id
        layers[name] = doc.Layers.Add(layer)
        return layers[name]

    def ensure_mat(name, rgb, **kw):
        if name in mats:
            return mats[name]
        m = r3d.Material()
        m.Name = name
        m.DiffuseColor = (*rgb, 255)
        m.Transparency = kw.get("transparency", 0.0)
        m.Shine = (1.0 - kw.get("roughness", 0.5)) * 200
        m.IndexOfRefraction = kw.get("ior", 1.5)
        m.SetUserString("VRayHint", name)
        m.SetUserString("Roughness", str(kw.get("roughness", 0.5)))
        try:
            m.ToPhysicallyBased()
            p = m.PhysicallyBased
            if p:
                p.Roughness = kw.get("roughness", 0.5)
                p.Opacity = 1.0 - kw.get("transparency", 0.0)
                if kw.get("transparency", 0) > 0.2:
                    p.OpacityIOR = kw.get("ior", 1.49)
        except Exception:
            pass
        mats[name] = doc.Materials.Add(m)
        return mats[name]

    for n, c in PARENTS:
        ensure_layer(n, c)

    objs = sorted(PARTS.glob("*.obj"))
    print(f"Found {len(objs)} parts")
    for path in objs:
        name = path.stem
        layer_name, mat_name, rgb, kw = match_rule(name)
        parent = layer_name.split("::")[0]
        ensure_layer(layer_name, rgb, parent=parent)
        ensure_mat(mat_name, rgb, **kw)

        verts, faces = parse_obj(path)
        if not verts or not faces:
            print("skip empty", name)
            continue
        # OBJs exported with up_axis=Z forward_axis=Y — coords already Rhino Z-up mm
        mesh = r3d.Mesh()
        for x, y, z in verts:
            mesh.Vertices.Add(x, y, z)
        for face in faces:
            if len(face) == 3:
                mesh.Faces.AddFace(face[0], face[1], face[2])
            elif len(face) == 4:
                mesh.Faces.AddFace(face[0], face[1], face[2], face[3])
            else:
                # fan
                for i in range(1, len(face) - 1):
                    mesh.Faces.AddFace(face[0], face[i], face[i + 1])
        mesh.Normals.ComputeNormals()
        mesh.Compact()

        attrs = r3d.ObjectAttributes()
        attrs.Name = name
        attrs.LayerIndex = layers[layer_name]
        attrs.MaterialIndex = mats[mat_name]
        attrs.MaterialSource = r3d.ObjectMaterialSource.MaterialFromObject
        doc.Objects.Add(mesh, attrs)
        print(f"  + {name}: {len(verts)}v {len(faces)}f -> {layer_name}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    assert doc.Write(str(OUT), 8)
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes, {len(doc.Objects)} objects)")


if __name__ == "__main__":
    main()
