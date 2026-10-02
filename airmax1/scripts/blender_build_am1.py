#!/usr/bin/env python3
"""
Blender headless builder — realistic Nike Air Max 1 (US9 Left).

Creates organic subdivided geometry from Nike FZ5808-102 proportions,
exports component meshes, then a companion script packs them into .3dm.
"""

import math
import os
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Matrix, Vector

# ---------------------------------------------------------------------------
# Spec (mm → Blender units: 0.001 m so 1 BU = 1 m; we work in mm then scale)
# Use millimeters directly as Blender units for CAD friendliness, then
# set unit scale on export. Rhino import will treat vertex coords as mm.
# ---------------------------------------------------------------------------

OUT_DIR = Path("/workspace/airmax1/output/blender_parts")
BLEND_PATH = Path("/workspace/airmax1/output/AirMax1_US9.blend")
RENDER_DIR = Path("/workspace/airmax1/output/renders")

L = 295.0
HEEL_STACK = 32.2
FF_STACK = 20.1
OUTSOLE_T = 5.5
HEEL_W = 81.8
FF_W = 107.9


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def sole_half_width(x):
    t = x / L
    if t < 0.15:
        return lerp(HEEL_W * 0.48, HEEL_W * 0.50, t / 0.15)
    if t < 0.42:
        return lerp(HEEL_W * 0.50, FF_W * 0.47, smoothstep((t - 0.15) / 0.27))
    if t < 0.72:
        return lerp(FF_W * 0.47, FF_W * 0.50, smoothstep((t - 0.42) / 0.30))
    if t < 0.90:
        return lerp(FF_W * 0.50, 36.0, smoothstep((t - 0.72) / 0.18))
    return lerp(36.0, 14.0, smoothstep((t - 0.90) / 0.10))


def outsole_bottom_z(x):
    t = x / L
    z = 0.0
    if t > 0.82:
        z += 4.0 * smoothstep((t - 0.82) / 0.18)
    if t < 0.05:
        z += 1.5 * (1 - t / 0.05)
    return z


def outsole_top_z(x):
    return outsole_bottom_z(x) + OUTSOLE_T


def midsole_top_z(x):
    t = x / L
    z = lerp(HEEL_STACK, FF_STACK, smoothstep(min(1.0, t / 0.88)))
    if t > 0.90:
        z += 2.2 * smoothstep((t - 0.90) / 0.10)
    return z


def mudguard_height(x):
    t = x / L
    if t < 0.10:
        return lerp(17.0, 15.0, t / 0.10)
    if t < 0.32:
        return lerp(15.0, 7.0, smoothstep((t - 0.10) / 0.22))
    if t < 0.52:
        return 7.0
    if t < 0.72:
        return lerp(7.0, 15.0, smoothstep((t - 0.52) / 0.20))
    if t < 0.88:
        return lerp(15.0, 21.0, smoothstep((t - 0.72) / 0.16))
    return lerp(21.0, 15.0, (t - 0.88) / 0.12)


def collar_z(x):
    t = x / L
    if t < 0.04:
        return lerp(55.0, 78.0, t / 0.04)
    if t < 0.20:
        return lerp(78.0, 74.0, (t - 0.04) / 0.16)
    if t < 0.38:
        return lerp(74.0, 60.0, smoothstep((t - 0.20) / 0.18))
    if t < 0.58:
        return lerp(60.0, 55.0, (t - 0.38) / 0.20)
    if t < 0.75:
        return lerp(55.0, 50.0, smoothstep((t - 0.58) / 0.17))
    if t < 0.90:
        return lerp(50.0, 38.0, smoothstep((t - 0.75) / 0.15))
    return lerp(38.0, 22.0, smoothstep((t - 0.90) / 0.10))


def tongue_z(x):
    t = x / L
    base = collar_z(x)
    if t < 0.30 or t > 0.80:
        return base
    u = (t - 0.30) / 0.50
    return max(base, 108.0 * (math.sin(math.pi * u) ** 1.05))


# ---------------------------------------------------------------------------
# Scene helpers
# ---------------------------------------------------------------------------

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 0.001  # 1 BU = 1 mm when displayed as meters*0.001
    # Actually: keep coords in mm, set scale so exports stay in mm numerically
    scene.unit_settings.scale_length = 1.0
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1000
    scene.render.filepath = str(RENDER_DIR / "preview_")
    # EEVEE
    if hasattr(scene, "eevee"):
        scene.eevee.taa_render_samples = 64


def new_mat(name, color, *, metallic=0.0, roughness=0.5, alpha=1.0, ior=1.45):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if alpha < 1.0:
            bsdf.inputs["Alpha"].default_value = alpha
            mat.blend_method = "BLEND"
            # Transmission for clear materials (Blender 4)
            if "Transmission Weight" in bsdf.inputs:
                bsdf.inputs["Transmission Weight"].default_value = 1.0 - alpha
            elif "Transmission" in bsdf.inputs:
                bsdf.inputs["Transmission"].default_value = 1.0 - alpha
            if "IOR" in bsdf.inputs:
                bsdf.inputs["IOR"].default_value = ior
    return mat


def assign_mat(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def smooth_obj(obj, levels=2):
    mod = obj.modifiers.new("Subsurf", "SUBSURF")
    mod.levels = levels
    mod.render_levels = levels + 1
    for p in obj.data.polygons:
        p.use_smooth = True


def apply_mods(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.select_set(False)


def mesh_from_sections(name, sections, cap=True):
    """sections: list of list of Vector (closed rings, same count)."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    rings = []
    for sec in sections:
        ring = [bm.verts.new(v) for v in sec]
        rings.append(ring)
    bm.verts.ensure_lookup_table()

    n = len(rings[0])
    for r in range(len(rings) - 1):
        for i in range(n):
            v0 = rings[r][i]
            v1 = rings[r][(i + 1) % n]
            v2 = rings[r + 1][(i + 1) % n]
            v3 = rings[r + 1][i]
            try:
                bm.faces.new([v0, v1, v2, v3])
            except ValueError:
                pass

    if cap and len(rings) >= 2:
        # fan caps
        for ring, flip in ((rings[0], True), (rings[-1], False)):
            c = Vector((0, 0, 0))
            for v in ring:
                c += v.co
            c /= len(ring)
            cv = bm.verts.new(c)
            for i in range(n):
                a = ring[i]
                b = ring[(i + 1) % n]
                try:
                    if flip:
                        bm.faces.new([cv, b, a])
                    else:
                        bm.faces.new([cv, a, b])
                except ValueError:
                    pass

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    return obj


def oval_ring(x, half_w, z0, z1, count=48, squat_bot=0.45, squat_top=0.85, y_scale=1.0):
    h = max(1.0, z1 - z0)
    cz = 0.5 * (z0 + z1)
    pts = []
    for i in range(count):
        a = 2 * math.pi * i / count
        sy = math.sin(a)
        cz_n = math.cos(a)
        y = half_w * y_scale * sy
        exp = squat_bot if cz_n < 0 else squat_top
        z = cz + (h * 0.5) * math.copysign(abs(cz_n) ** exp, cz_n)
        pts.append(Vector((x, y, z)))
    return pts


def last_ring(x, inset=0.0, count=64):
    """Organic upper last cross-section."""
    z0 = midsole_top_z(x) + 0.4
    z1 = collar_z(x)
    hw0 = max(6.0, sole_half_width(x) * 0.90 - inset)
    pts = []
    for i in range(count):
        a = 2 * math.pi * i / count
        sy = math.sin(a)
        cz_n = math.cos(a)
        if cz_n < -0.15:
            # bottom of upper (on midsole)
            y = hw0 * sy * 0.98
            z = z0 + 0.8 * (1 - abs(sy))
        else:
            u = (cz_n + 0.15) / 1.15  # 0..1 toward top
            u = clamp(u, 0, 1)
            # AM1 last: fuller mid, taper to collar, slight medial asymmetry later
            hw = hw0 * lerp(1.0, 0.68, u ** 1.2)
            y = hw * sy
            # vamp curve — higher crown on top
            z = z0 + (z1 - z0) * (u ** 0.72)
            # push sides slightly for volume
            if 0.15 < u < 0.7:
                y *= 1.0 + 0.04 * math.sin(math.pi * (u - 0.15) / 0.55)
        pts.append(Vector((x, y, z)))
    return pts


def solidify(obj, thickness, offset=0.0):
    mod = obj.modifiers.new("Solidify", "SOLIDIFY")
    mod.thickness = thickness
    mod.offset = offset
    mod.use_even_offset = True
    mod.use_quality_normals = True
    return mod


def boolean_diff(obj, cutter, name="Bool"):
    mod = obj.modifiers.new(name, "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    return mod


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------

def build_outsole():
    xs = [i * L / 40 for i in range(41)]
    secs = [
        oval_ring(x, sole_half_width(x) * 0.98, outsole_bottom_z(x), outsole_top_z(x), 56, 0.3, 0.55)
        for x in xs
    ]
    obj = mesh_from_sections("Outsole_Base", secs)
    smooth_obj(obj, 2)
    apply_mods(obj)
    assign_mat(obj, new_mat("MAT_Rubber", (0.05, 0.05, 0.05), roughness=0.72))
    return obj


def build_waffle():
    objs = []
    mat = new_mat("MAT_Rubber_Waffle", (0.04, 0.04, 0.04), roughness=0.75)
    # Forefoot waffle
    for ix in range(8):
        for iy in range(-4, 5):
            x = 140 + ix * 12.5
            y = iy * 10.0
            if abs(y) > sole_half_width(x) - 10:
                continue
            bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, outsole_bottom_z(x) - 1.2))
            o = bpy.context.active_object
            o.name = f"Waffle_FF_{ix}_{iy}"
            o.scale = (6.2, 6.2, 2.6)
            bpy.ops.object.transform_apply(scale=True)
            # bevel
            bm = bmesh.new()
            bm.from_mesh(o.data)
            bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.6, segments=2, affect="EDGES")
            bm.to_mesh(o.data)
            bm.free()
            for p in o.data.polygons:
                p.use_smooth = True
            assign_mat(o, mat)
            objs.append(o)
    # Heel pods
    for ix in range(3):
        for iy in range(-2, 3):
            x = 15 + ix * 14
            y = iy * 11
            if abs(y) > sole_half_width(x) - 8:
                continue
            bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, outsole_bottom_z(x) - 1.3))
            o = bpy.context.active_object
            o.name = f"Waffle_Heel_{ix}_{iy}"
            o.scale = (9.5, 8.5, 2.8)
            bpy.ops.object.transform_apply(scale=True)
            bm = bmesh.new()
            bm.from_mesh(o.data)
            bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.8, segments=2, affect="EDGES")
            bm.to_mesh(o.data)
            bm.free()
            for p in o.data.polygons:
                p.use_smooth = True
            assign_mat(o, mat)
            objs.append(o)
    return objs


def build_midsole():
    xs = [i * L / 48 for i in range(49)]
    secs = []
    for x in xs:
        t = x / L
        waist = 1.0 - 0.05 * math.sin(math.pi * clamp((t - 0.12) / 0.55, 0, 1))
        secs.append(
            oval_ring(
                x,
                sole_half_width(x) * 0.995 * waist,
                outsole_top_z(x) - 0.4,
                midsole_top_z(x),
                64,
                0.38,
                0.75,
            )
        )
    obj = mesh_from_sections("Midsole_Foam", secs)
    smooth_obj(obj, 2)

    # Air window cutter (capsule)
    cx, cz = 42.0, 16.8
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32, radius=9.0, depth=48.0, location=(cx, 0, cz), rotation=(0, math.pi / 2, 0)
    )
    cutter = bpy.context.active_object
    cutter.name = "AirCutter"
    # Flatten ends into capsule via scale on Y (through midsole width)
    cutter.scale = (1.0, sole_half_width(cx) * 1.05 / 9.0, 1.15)
    bpy.ops.object.transform_apply(scale=True)
    smooth_obj(cutter, 1)
    apply_mods(cutter)

    boolean_diff(obj, cutter)
    apply_mods(obj)
    # hide cutter
    cutter.hide_set(True)
    cutter.hide_render = True

    assign_mat(obj, new_mat("MAT_Foam", (0.95, 0.95, 0.93), roughness=0.82))
    return obj, cutter


def build_air_unit():
    cx, cz = 42.0, 16.8
    hl, hh = 23.5, 8.4
    hw = sole_half_width(cx) * 0.82
    # Clear window shell
    secs = []
    for i in range(18):
        t = i / 17
        x = cx - hl + (hl * 2) * t
        if t < 0.12:
            s = math.sin((t / 0.12) * math.pi / 2)
        elif t > 0.88:
            s = math.sin(((1 - t) / 0.12) * math.pi / 2)
        else:
            s = 1.0
        h = hh * (0.7 + 0.3 * s)
        secs.append(oval_ring(x, hw * (0.9 + 0.1 * s), cz - h, cz + h, 40, 0.95, 0.95))
    window = mesh_from_sections("AirUnit_Window", secs)
    smooth_obj(window, 2)
    apply_mods(window)
    assign_mat(
        window,
        new_mat("MAT_AirClear", (0.75, 0.88, 0.95), roughness=0.05, alpha=0.25, ior=1.49),
    )

    # Membrane
    mem_secs = []
    for i in range(14):
        t = i / 13
        x = cx - hl + 4 + (hl * 2 - 8) * t
        mem_secs.append(oval_ring(x, hw * 0.65, cz - hh * 0.7, cz + hh * 0.7, 32, 0.98, 0.98))
    membrane = mesh_from_sections("AirUnit_Membrane", mem_secs)
    smooth_obj(membrane, 2)
    apply_mods(membrane)
    assign_mat(
        membrane,
        new_mat("MAT_AirMem", (0.7, 0.8, 0.88), roughness=0.25, alpha=0.45, ior=1.4),
    )

    # Pillars
    pillars = []
    mat_p = new_mat("MAT_AirPillar", (0.65, 0.75, 0.85), roughness=0.2, alpha=0.55, ior=1.45)
    for i in range(3):
        t = (i + 1) / 4
        x = cx - hl + (hl * 2) * t
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 0, cz))
        p = bpy.context.active_object
        p.name = f"AirUnit_Pillar_{i+1}"
        p.scale = (2.6, hw * 0.95, hh * 1.5)
        bpy.ops.object.transform_apply(scale=True)
        bm = bmesh.new()
        bm.from_mesh(p.data)
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.4, segments=2, affect="EDGES")
        bm.to_mesh(p.data)
        bm.free()
        for poly in p.data.polygons:
            poly.use_smooth = True
        assign_mat(p, mat_p)
        pillars.append(p)
    return [window, membrane] + pillars


def build_upper_last():
    xs = [4 + i * (L - 10) / 56 for i in range(57)]
    secs = [last_ring(x, 0.0, 72) for x in xs]
    obj = mesh_from_sections("Upper_Mesh_Last", secs)
    smooth_obj(obj, 3)
    apply_mods(obj)
    # Soften as a slightly inset shell look via displace-free solidify thin wall
    # Use only a mild solidify so overlays can sit outside
    solidify(obj, 1.8, offset=1.0)
    apply_mods(obj)
    assign_mat(obj, new_mat("MAT_Mesh", (0.96, 0.96, 0.95), roughness=0.88))
    return obj


def build_side_band(name, z0_fn, z1_fn, xs, thickness=1.7, y_factor=0.94, mat=None, count=48):
    """Lateral+medial thin bands following last exterior."""
    objs = []
    for sign, tag in ((1.0, "Lateral"), (-1.0, "Medial")):
        # Build as loft of vertical edge strips (open surface) then solidify
        sections = []
        for x in xs:
            z0 = z0_fn(x)
            z1 = z1_fn(x)
            # sample last outer Y at mid height
            pts = []
            n = 10
            for j in range(n):
                u = j / (n - 1)
                z = lerp(z0, z1, u)
                # width from last approximation
                hw = sole_half_width(x) * y_factor
                # taper toward top
                tap = lerp(1.0, 0.78, clamp((z - midsole_top_z(x)) / max(1, collar_z(x) - midsole_top_z(x)), 0, 1))
                y = sign * hw * tap
                # slight outward for overlay sitting on upper
                y += sign * 0.6
                pts.append(Vector((x, y, z)))
            sections.append(pts)
        # Open strip loft
        mesh = bpy.data.meshes.new(f"{name}_{tag}")
        obj = bpy.data.objects.new(f"{name}_{tag}", mesh)
        bpy.context.collection.objects.link(obj)
        bm = bmesh.new()
        rings = [[bm.verts.new(v) for v in sec] for sec in sections]
        bm.verts.ensure_lookup_table()
        for r in range(len(rings) - 1):
            for i in range(len(rings[0]) - 1):
                try:
                    bm.faces.new([rings[r][i], rings[r][i + 1], rings[r + 1][i + 1], rings[r + 1][i]])
                except ValueError:
                    pass
        bm.to_mesh(mesh)
        bm.free()
        solidify(obj, thickness, offset=1.0)
        smooth_obj(obj, 2)
        apply_mods(obj)
        if mat:
            assign_mat(obj, mat)
        objs.append(obj)
    return objs


def build_mudguard():
    mat = new_mat("MAT_LeatherBlk", (0.04, 0.04, 0.04), roughness=0.42)
    xs = [2 + i * (L - 4) / 56 for i in range(57)]
    return build_side_band(
        "Mudguard",
        lambda x: midsole_top_z(x) - 0.5,
        lambda x: midsole_top_z(x) + mudguard_height(x),
        xs,
        thickness=1.9,
        y_factor=0.96,
        mat=mat,
    )


def build_suede():
    mat = new_mat("MAT_Suede", (0.78, 0.75, 0.70), roughness=0.92)
    xs_q = [68 + i * 130 / 36 for i in range(37)]
    quarters = build_side_band(
        "Quarter_Suede",
        lambda x: midsole_top_z(x) + mudguard_height(x) - 1.0,
        lambda x: lerp(midsole_top_z(x) + mudguard_height(x) + 26, collar_z(x) - 5, clamp((x - 68) / 120, 0, 1)),
        xs_q,
        thickness=1.5,
        y_factor=0.91,
        mat=mat,
    )
    xs_h = [2 + i * 68 / 24 for i in range(25)]
    heels = build_side_band(
        "HeelCounter",
        lambda x: midsole_top_z(x) + mudguard_height(x) - 0.5,
        lambda x: collar_z(x) - 3,
        xs_h,
        thickness=1.6,
        y_factor=0.90,
        mat=mat,
    )
    return quarters + heels


def build_swoosh():
    mat = new_mat("MAT_Swoosh", (0.03, 0.03, 0.03), roughness=0.38)
    objs = []
    # Smooth swoosh via curve spine + bevel
    spine_pts = [
        (168, 0.72, 6, 3.2),
        (158, 0.84, 8, 5.0),
        (148, 0.93, 11, 7.5),
        (136, 0.98, 15, 10.0),
        (124, 0.99, 20, 11.0),
        (112, 0.94, 26, 10.0),
        (100, 0.85, 31, 8.0),
        (90, 0.70, 35, 5.5),
        (82, 0.52, 36, 3.5),
        (76, 0.34, 34, 2.0),
    ]
    for sign, tag in ((1.0, "Lateral"), (-1.0, "Medial")):
        curve_data = bpy.data.curves.new(f"SwooshCrv_{tag}", type="CURVE")
        curve_data.dimensions = "3D"
        curve_data.resolution_u = 32
        curve_data.fill_mode = "FULL"
        curve_data.bevel_depth = 0.0
        spline = curve_data.splines.new("NURBS")
        spline.points.add(len(spine_pts) - 1)
        widths = []
        for i, (x, yf, zadd, wh) in enumerate(spine_pts):
            y = sign * sole_half_width(x) * yf * 0.93
            z = midsole_top_z(x) + mudguard_height(x) + zadd
            spline.points[i].co = (x, y + sign * 1.2, z, 1)
            widths.append(wh)
        spline.use_endpoint_u = True
        spline.order_u = 4

        # Build tapered tube manually along spine
        secs = []
        for i, (x, yf, zadd, wh) in enumerate(spine_pts):
            y = sign * sole_half_width(x) * yf * 0.93 + sign * 1.2
            z = midsole_top_z(x) + mudguard_height(x) + zadd
            ring = []
            for k in range(16):
                a = 2 * math.pi * k / 16
                # flatten against shoe (thinner in Y)
                ring.append(
                    Vector(
                        (
                            x + 1.6 * math.cos(a),
                            y + sign * 0.55 * abs(math.cos(a)),
                            z + wh * math.sin(a),
                        )
                    )
                )
            secs.append(ring)
        obj = mesh_from_sections(f"Swoosh_{tag}", secs)
        smooth_obj(obj, 2)
        apply_mods(obj)
        assign_mat(obj, mat)
        objs.append(obj)
        # remove unused curve
        bpy.data.curves.remove(curve_data)
    return objs


def build_tongue():
    xs = [108 + i * 100 / 28 for i in range(29)]
    secs = []
    for x in xs:
        t = (x - 108) / 100
        w = lerp(20, 14, t)
        z_top = tongue_z(x)
        z_bot = max(collar_z(x) - 6, midsole_top_z(x) + 30)
        ring = []
        for k in range(24):
            a = 2 * math.pi * k / 24
            y = w * math.sin(a)
            # flatter tongue pad
            z = 0.5 * (z_bot + z_top) + 0.5 * (z_top - z_bot) * math.cos(a) * 0.85
            if math.cos(a) < 0:
                z = z_bot + 1.5 * abs(math.cos(a))
            ring.append(Vector((x, y, z)))
        secs.append(ring)
    obj = mesh_from_sections("Tongue", secs)
    smooth_obj(obj, 2)
    apply_mods(obj)
    assign_mat(obj, new_mat("MAT_Tongue", (0.97, 0.97, 0.96), roughness=0.8))
    return obj


def build_collar():
    mat = new_mat("MAT_Collar", (0.94, 0.94, 0.93), roughness=0.8)
    xs = [4 + i * 120 / 30 for i in range(31)]
    return build_side_band(
        "Collar",
        lambda x: collar_z(x) - 14,
        collar_z,
        xs,
        thickness=3.2,
        y_factor=0.88,
        mat=mat,
    )


def build_laces_hardware():
    objs = []
    mat_l = new_mat("MAT_Lace", (0.95, 0.95, 0.94), roughness=0.7)
    mat_p = new_mat("MAT_Plastic", (0.08, 0.08, 0.08), roughness=0.3, metallic=0.05)
    for i in range(6):
        x = 112 + i * 14
        z = collar_z(x) - 10
        # lace as curve bevel
        curve = bpy.data.curves.new(f"LaceCrv_{i}", "CURVE")
        curve.dimensions = "3D"
        curve.bevel_depth = 1.4
        curve.bevel_resolution = 4
        curve.resolution_u = 12
        sp = curve.splines.new("NURBS")
        pts = [(x, -10.5, z), (x + 4, 0, z + 5), (x, 10.5, z)]
        sp.points.add(len(pts) - 1)
        for j, p in enumerate(pts):
            sp.points[j].co = (*p, 1)
        sp.use_endpoint_u = True
        sp.order_u = 3
        obj = bpy.data.objects.new(f"Lace_{i+1}", curve)
        bpy.context.collection.objects.link(obj)
        assign_mat(obj, mat_l)
        # convert to mesh
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.convert(target="MESH")
        obj.select_set(False)
        for p in obj.data.polygons:
            p.use_smooth = True
        objs.append(obj)

        for sign, tag in ((1.0, "L"), (-1.0, "M")):
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=16, radius=2.0, depth=2.2, location=(x, sign * 10.8, z), rotation=(math.pi / 2, 0, 0)
            )
            e = bpy.context.active_object
            e.name = f"Eyelet_{tag}_{i+1}"
            for p in e.data.polygons:
                p.use_smooth = True
            assign_mat(e, mat_p)
            objs.append(e)

    # Lace locks
    for sign, tag in ((1.0, "L"), (-1.0, "M")):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(102, sign * 11.2, collar_z(102) - 8))
        o = bpy.context.active_object
        o.name = f"LaceLock_{tag}"
        o.scale = (9, 5.5, 7)
        bpy.ops.object.transform_apply(scale=True)
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=1.2, segments=3, affect="EDGES")
        bm.to_mesh(o.data)
        bm.free()
        for p in o.data.polygons:
            p.use_smooth = True
        assign_mat(o, mat_p)
        objs.append(o)
    return objs


def build_insole():
    xs = [14 + i * (L - 32) / 36 for i in range(37)]
    secs = [
        oval_ring(x, sole_half_width(x) * 0.74, midsole_top_z(x) + 0.6, midsole_top_z(x) + 4.2, 40, 0.25, 0.5)
        for x in xs
    ]
    obj = mesh_from_sections("Insole", secs)
    smooth_obj(obj, 2)
    apply_mods(obj)
    assign_mat(obj, new_mat("MAT_Insole", (0.9, 0.88, 0.84), roughness=0.8))
    return obj


def setup_lights_camera():
    # Soft studio — mm-scale world: use SUN lights (direction only) + dim areas
    bpy.ops.object.light_add(type="SUN", location=(200, -300, 400))
    key = bpy.context.active_object
    key.data.energy = 3.5
    key.rotation_euler = (math.radians(45), math.radians(15), math.radians(-20))
    key.name = "KeyLight"

    bpy.ops.object.light_add(type="SUN", location=(100, 300, 200))
    fill = bpy.context.active_object
    fill.data.energy = 1.2
    fill.rotation_euler = (math.radians(60), math.radians(-20), math.radians(160))
    fill.name = "FillLight"

    bpy.ops.object.light_add(type="AREA", location=(400, -150, 250))
    rim = bpy.context.active_object
    rim.data.energy = 200000
    rim.data.size = 350
    rim.name = "RimLight"

    bpy.ops.mesh.primitive_plane_add(size=1200, location=(150, 0, -1))
    ground = bpy.context.active_object
    ground.name = "Ground"
    assign_mat(ground, new_mat("Ground", (0.92, 0.92, 0.90), roughness=0.95))

    bpy.ops.object.camera_add(location=(150, -520, 70), rotation=(math.radians(84), 0, 0))
    cam = bpy.context.active_object
    cam.name = "Cam_Lateral"
    cam.data.lens = 80
    cam.data.clip_end = 10000
    bpy.context.scene.camera = cam

    # World ambient
    world = bpy.data.worlds.new("StudioWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.85, 0.85, 0.84, 1)
    bg.inputs[1].default_value = 0.6
    return cam


def render_views():
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    cam = scene.camera
    # Target shoe center
    target = Vector((148, 0, 45))
    views = [
        ("lateral", Vector((148, -560, 55))),
        ("threequarter", Vector((340, -380, 160))),
        ("heel", Vector((-220, 0, 70))),
        ("top", Vector((148, 0, 520))),
    ]
    for name, loc in views:
        cam.location = loc
        direction = target - cam.location
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(RENDER_DIR / f"am1_{name}")
        bpy.ops.render.render(write_still=True)
        print("rendered", name)


def export_parts():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    skip = {"Ground", "KeyLight", "FillLight", "RimLight", "Cam_Lateral", "AirCutter"}
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        if obj.name in skip or obj.name.startswith("AirCutter"):
            continue
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        path = OUT_DIR / f"{obj.name}.obj"
        bpy.ops.wm.obj_export(
            filepath=str(path),
            export_selected_objects=True,
            export_materials=True,
            export_smooth_groups=False,
            apply_modifiers=True,
            forward_axis="Y",
            up_axis="Z",
        )
        obj.select_set(False)
        print("exported", path.name)


def main():
    reset_scene()
    print("Building outsole...")
    build_outsole()
    print("Building waffle...")
    build_waffle()
    print("Building midsole...")
    build_midsole()
    print("Building air unit...")
    build_air_unit()
    print("Building upper...")
    build_upper_last()
    print("Building mudguard...")
    build_mudguard()
    print("Building suede...")
    build_suede()
    print("Building swoosh...")
    build_swoosh()
    print("Building collar...")
    build_collar()
    print("Building tongue...")
    build_tongue()
    print("Building laces/hardware...")
    build_laces_hardware()
    print("Building insole...")
    build_insole()

    setup_lights_camera()
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    print("saved blend", BLEND_PATH)

    print("Rendering...")
    render_views()
    print("Exporting parts...")
    export_parts()
    print("DONE")


if __name__ == "__main__":
    main()
