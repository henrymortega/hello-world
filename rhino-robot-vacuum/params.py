"""Modern home robot vacuum — millimetres, Z-up, body centred on origin.

Floor is z=0. Wheels rest on the floor; the body floats a few millimetres above.
"""

# Ride height
CLEARANCE = 12.0  # underside of body above floor

# Main body (squat disc)
BODY_R = 175.0
BODY_H = 52.0
BODY_Z0 = CLEARANCE
TOP_DOME_H = 14.0  # soft crown above the cylinder

# Soft bumper (front 180°)
BUMPER_R = 178.0
BUMPER_H = 28.0
BUMPER_Z = BODY_Z0 + 6.0
BUMPER_THICK = 8.0

# LIDAR turret
LIDAR_R = 28.0
LIDAR_H = 22.0
LIDAR_Z = BODY_Z0 + BODY_H + TOP_DOME_H - 2.0
LIDAR_CAP_R = 24.0
LIDAR_WINDOW_R = 27.0
LIDAR_WINDOW_H = 8.0
LIDAR_WINDOW_R_IN = 22.0

# Power / home button on top
BUTTON_R = 9.0
BUTTON_Z = BODY_Z0 + BODY_H + TOP_DOME_H - 1.0
BUTTON_X = -55.0

# Status LED ring around button
LED_R_OUT = 14.0
LED_R_IN = 11.0

# Front cliff / IR sensor strip
SENSOR_W = 90.0
SENSOR_D = 8.0
SENSOR_H = 6.0
SENSOR_Y = BODY_R - 12.0
SENSOR_Z = BODY_Z0 + 18.0

# Drive wheels (left / right) — centres at wheel radius so they sit on the floor
WHEEL_R = 32.0
WHEEL_W = 18.0
WHEEL_X = 55.0
WHEEL_Z = WHEEL_R

# Front caster
CASTER_R = 12.0
CASTER_Y = BODY_R - 55.0
CASTER_Z = CASTER_R

# Side brush (right-front)
SIDE_BRUSH_R = 38.0
SIDE_BRUSH_X = 95.0
SIDE_BRUSH_Y = 110.0
SIDE_BRUSH_Z = 3.0
SIDE_BRUSH_HUB_R = 10.0

# Main roller brush under body
ROLLER_L = 140.0
ROLLER_R = 14.0
ROLLER_Y = -20.0
ROLLER_Z = ROLLER_R + 2.0

# Charging contacts
CONTACT_W = 12.0
CONTACT_D = 18.0
CONTACT_H = 2.0
CONTACT_Y = -BODY_R + 35.0

# Dustbin door indent (rear)
BIN_W = 110.0
BIN_D = 55.0
BIN_H = 4.0
BIN_Y = -BODY_R + 50.0
BIN_Z = BODY_Z0 + BODY_H + TOP_DOME_H - 3.0

# Colours
WHITE = (236, 238, 242, 255)
CHARCOAL = (42, 44, 48, 255)
DARK = (28, 30, 34, 255)
ACCENT = (64, 168, 255, 255)  # cool LED blue
SILVER = (180, 186, 194, 255)
RUBBER = (22, 22, 24, 255)
SMOKE = (120, 128, 136, 255)

# Layers
LAYER_BODY = "01_Body"
LAYER_BUMPER = "02_Bumper"
LAYER_LIDAR = "03_Lidar"
LAYER_CONTROLS = "04_Controls"
LAYER_WHEELS = "05_Wheels"
LAYER_BRUSHES = "06_Brushes"
LAYER_SENSORS = "07_Sensors"
LAYER_CONSTRUCTION = "00_Construction"
