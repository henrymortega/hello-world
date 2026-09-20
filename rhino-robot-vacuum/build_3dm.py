"""Write robot_vacuum.3dm — modern disc robot vacuum."""

from __future__ import annotations

import math
from pathlib import Path

import rhino3dm as r3d

import params as P
from geom import arc_bumper, box, cylinder_z, pipe_z, revolve_profile, sphere, torus, wheel

OUT = Path(__file__).resolve().parent / "robot_vacuum.3dm"


def _layer(name, color, visible=True):
    layer = r3d.Layer()
    layer.Name = name
    layer.Color = color
    layer.Visible = visible
    return layer


def _attr(layer_index, name, color, material_index):
    attr = r3d.ObjectAttributes()
    attr.LayerIndex = layer_index
    attr.Name = name
    attr.ColorSource = r3d.ObjectColorSource.ColorFromObject
    attr.ObjectColor = color
    attr.MaterialSource = r3d.ObjectMaterialSource.MaterialFromObject
    attr.MaterialIndex = material_index
    return attr


def add_mat(f, name, diffuse, transparency=0.0, ior=1.0, reflect=0.0):
    mat = r3d.Material()
    mat.Name = name
    mat.DiffuseColor = diffuse
    mat.Transparency = transparency
    mat.IndexOfRefraction = ior
    mat.Reflectivity = reflect
    return f.Materials.Add(mat)


def add(f, geom, layer_i, name, color, mat_i):
    if geom is None:
        print("skip", name)
        return
    attr = _attr(layer_i, name, color, mat_i)
    if isinstance(geom, r3d.Brep):
        f.Objects.AddBrep(geom, attr)
    elif isinstance(geom, r3d.Extrusion):
        f.Objects.AddExtrusion(geom, attr)
    elif isinstance(geom, r3d.Sphere):
        f.Objects.AddSphere(geom, attr)
    else:
        f.Objects.Add(geom, attr)


def soft_body():
    """Main white body: cylinder + soft revolved crown."""
    body = cylinder_z(0, 0, P.BODY_Z0, P.BODY_H, P.BODY_R)
    r = P.BODY_R
    h0 = P.BODY_Z0 + P.BODY_H
    h1 = h0 + P.TOP_DOME_H
    dome = revolve_profile(
        [
            (r - 0.5, h0),
            (r - 4.0, h0 + 4.0),
            (r * 0.55, h1 - 1.5),
            (0.0, h1),
        ]
    )
    return body, dome


def main():
    f = r3d.File3dm()
    f.Settings.ModelUnitSystem = r3d.UnitSystem.Millimeters
    f.Settings.ModelAbsoluteTolerance = 0.01

    layers = [
        _layer(P.LAYER_CONSTRUCTION, (160, 160, 160, 255), False),
        _layer(P.LAYER_BODY, P.WHITE),
        _layer(P.LAYER_BUMPER, P.CHARCOAL),
        _layer(P.LAYER_LIDAR, P.DARK),
        _layer(P.LAYER_CONTROLS, P.ACCENT),
        _layer(P.LAYER_WHEELS, P.RUBBER),
        _layer(P.LAYER_BRUSHES, P.SMOKE),
        _layer(P.LAYER_SENSORS, P.SILVER),
    ]
    for layer in layers:
        f.Layers.Add(layer)
    idx = {layer.Name: i for i, layer in enumerate(layers)}

    m_white = add_mat(f, "matte-white", P.WHITE)
    m_charcoal = add_mat(f, "charcoal", P.CHARCOAL)
    m_dark = add_mat(f, "dark", P.DARK, reflect=0.15)
    m_led = add_mat(f, "led-blue", P.ACCENT, reflect=0.2)
    m_rubber = add_mat(f, "rubber", P.RUBBER)
    m_smoke = add_mat(f, "smoke", P.SMOKE, transparency=0.25, ior=1.4)
    m_silver = add_mat(f, "silver", P.SILVER, reflect=0.45)

    body, dome = soft_body()
    add(f, body, idx[P.LAYER_BODY], "body", P.WHITE, m_white)
    add(f, dome, idx[P.LAYER_BODY], "top-dome", P.WHITE, m_white)

    # Dustbin lid indent (rear recess as thin box sitting on top)
    add(
        f,
        box(
            -P.BIN_W * 0.5,
            P.BIN_W * 0.5,
            P.BIN_Y - P.BIN_D,
            P.BIN_Y,
            P.BIN_Z,
            P.BIN_Z + P.BIN_H,
        ),
        idx[P.LAYER_BODY],
        "dustbin-lid",
        P.WHITE,
        m_white,
    )

    bumper = arc_bumper(P.BUMPER_R, P.BUMPER_H, P.BUMPER_Z, P.BUMPER_THICK)
    add(f, bumper, idx[P.LAYER_BUMPER], "bumper", P.CHARCOAL, m_charcoal)

    # Soft bumper lip (thin torus-ish bead)
    add(f, torus(P.BODY_R - 1.0, 3.5, P.BUMPER_Z + P.BUMPER_H), idx[P.LAYER_BUMPER], "bumper-bead", P.CHARCOAL, m_charcoal)

    # LIDAR turret
    add(f, cylinder_z(0, 0, P.LIDAR_Z, P.LIDAR_H, P.LIDAR_R), idx[P.LAYER_LIDAR], "lidar-body", P.DARK, m_dark)
    add(
        f,
        pipe_z(0, 0, P.LIDAR_Z + 6.0, P.LIDAR_WINDOW_H, P.LIDAR_WINDOW_R, P.LIDAR_WINDOW_R_IN),
        idx[P.LAYER_LIDAR],
        "lidar-window",
        P.SMOKE,
        m_smoke,
    )
    add(
        f,
        cylinder_z(0, 0, P.LIDAR_Z + P.LIDAR_H - 2.0, 3.0, P.LIDAR_CAP_R),
        idx[P.LAYER_LIDAR],
        "lidar-cap",
        P.DARK,
        m_dark,
    )

    # Power button + LED ring
    add(
        f,
        cylinder_z(P.BUTTON_X, 0, P.BUTTON_Z, 2.5, P.BUTTON_R),
        idx[P.LAYER_CONTROLS],
        "power-button",
        P.DARK,
        m_dark,
    )
    add(
        f,
        pipe_z(P.BUTTON_X, 0, P.BUTTON_Z + 0.5, 1.5, P.LED_R_OUT, P.LED_R_IN),
        idx[P.LAYER_CONTROLS],
        "status-led",
        P.ACCENT,
        m_led,
    )

    # Front IR / cliff sensor bar
    add(
        f,
        box(
            -P.SENSOR_W * 0.5,
            P.SENSOR_W * 0.5,
            P.SENSOR_Y - P.SENSOR_D,
            P.SENSOR_Y,
            P.SENSOR_Z,
            P.SENSOR_Z + P.SENSOR_H,
        ),
        idx[P.LAYER_SENSORS],
        "front-sensors",
        P.SILVER,
        m_silver,
    )

    # Drive wheels
    add(
        f,
        wheel(-P.WHEEL_X, 0, P.WHEEL_Z, P.WHEEL_R, P.WHEEL_W, left=True),
        idx[P.LAYER_WHEELS],
        "wheel-left",
        P.RUBBER,
        m_rubber,
    )
    add(
        f,
        wheel(P.WHEEL_X, 0, P.WHEEL_Z, P.WHEEL_R, P.WHEEL_W, left=False),
        idx[P.LAYER_WHEELS],
        "wheel-right",
        P.RUBBER,
        m_rubber,
    )
    # Wheel hubs (axle caps on the outer face)
    add(f, cylinder_z(-P.WHEEL_X, 0, P.WHEEL_Z - 6, 12, 9), idx[P.LAYER_WHEELS], "hub-left", P.DARK, m_dark)
    add(f, cylinder_z(P.WHEEL_X, 0, P.WHEEL_Z - 6, 12, 9), idx[P.LAYER_WHEELS], "hub-right", P.DARK, m_dark)

    # Front caster
    add(f, sphere(0, P.CASTER_Y, P.CASTER_Z, P.CASTER_R), idx[P.LAYER_WHEELS], "caster", P.RUBBER, m_rubber)
    add(f, cylinder_z(0, P.CASTER_Y, P.CASTER_Z + 2, 10, 6), idx[P.LAYER_WHEELS], "caster-mount", P.DARK, m_dark)

    # Side brush
    add(
        f,
        cylinder_z(P.SIDE_BRUSH_X, P.SIDE_BRUSH_Y, P.SIDE_BRUSH_Z, 4.0, P.SIDE_BRUSH_HUB_R),
        idx[P.LAYER_BRUSHES],
        "side-brush-hub",
        P.DARK,
        m_dark,
    )
    # Three simple brush arms as thin boxes radiating out
    for i, ang in enumerate((20, 140, 260)):
        a = math.radians(ang)
        x1 = P.SIDE_BRUSH_X + P.SIDE_BRUSH_HUB_R * math.cos(a)
        y1 = P.SIDE_BRUSH_Y + P.SIDE_BRUSH_HUB_R * math.sin(a)
        x2 = P.SIDE_BRUSH_X + P.SIDE_BRUSH_R * math.cos(a)
        y2 = P.SIDE_BRUSH_Y + P.SIDE_BRUSH_R * math.sin(a)
        add(
            f,
            box(min(x1, x2) - 2, max(x1, x2) + 2, min(y1, y2) - 2, max(y1, y2) + 2, P.SIDE_BRUSH_Z, P.SIDE_BRUSH_Z + 3),
            idx[P.LAYER_BRUSHES],
            f"side-bristle-{i}",
            P.SMOKE,
            m_smoke,
        )

    # Main roller (axis along X)
    roller = wheel(0, P.ROLLER_Y, P.ROLLER_Z, P.ROLLER_R, P.ROLLER_L, left=False)
    # Re-centre roller on X=0
    if roller is not None:
        bb = roller.GetBoundingBox()
        cx = 0.5 * (bb.Min.X + bb.Max.X)
        roller.Translate(r3d.Vector3d(-cx, 0, 0))
    add(f, roller, idx[P.LAYER_BRUSHES], "main-roller", P.DARK, m_dark)

    # Charging contacts
    gap = 18.0
    for i, x in enumerate((-gap, gap)):
        add(
            f,
            box(
                x - P.CONTACT_W * 0.5,
                x + P.CONTACT_W * 0.5,
                P.CONTACT_Y - P.CONTACT_D * 0.5,
                P.CONTACT_Y + P.CONTACT_D * 0.5,
                0.5,
                0.5 + P.CONTACT_H,
            ),
            idx[P.LAYER_SENSORS],
            f"charge-contact-{i}",
            P.SILVER,
            m_silver,
        )

    f.Objects.AddTextDot(
        "Modern robot vacuum (mm)\n~350 mm diameter · wheels on z=0\nRun robot_vacuum.py in Rhino 8 to rebuild.",
        r3d.Point3d(0.0, -P.BODY_R - 40.0, 0.0),
    )
    f.Write(str(OUT), 8)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
