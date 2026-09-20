"""Stylized pirate spyglass — millimetres, axis along +X, eyepiece at the origin."""

# Eyepiece (gold cup)
EYE_X = 0.0
EYE_L = 11.0
EYE_R = 13.8

# Chrome draw tube
SILVER_X = 9.0
SILVER_L = 36.0
SILVER_R = 8.4

# Faceted leather / wood collar
COLLAR_X = 40.0
COLLAR_L = 26.0
COLLAR_R = 18.8
COLLAR_SIDES = 12

# Tapered wooden barrel
BARREL_X0 = 62.0
BARREL_X1 = 152.0
BARREL_R0 = 20.8
BARREL_R1 = 27.2

# Front wood rim (end grain ring)
RIM_X = 147.0
RIM_L = 12.0
RIM_R_OUT = 30.2
RIM_R_IN = 20.0

# Brass ring around the lens
RING_X = 154.5
RING_L = 2.8
RING_R_OUT = 20.2
RING_R_IN = 18.6

# Cyan glass
LENS_X = 155.2
LENS_L = 2.6
LENS_R = 18.4

# Top sight (box on the barrel)
SIGHT_X0 = 127.0
SIGHT_X1 = 149.0
SIGHT_Y0 = 25.2
SIGHT_Y1 = 39.0
SIGHT_Z0 = -6.8
SIGHT_Z1 = 6.8

# Colours (RGBA)
GOLD = (236, 186, 42, 255)
CHROME = (186, 198, 210, 255)
COLLAR = (102, 62, 28, 255)
WOOD = (210, 140, 45, 255)
WOOD_DARK = (150, 78, 30, 255)
LENS = (32, 186, 230, 255)

# Layers
LAYER_GOLD = "01_Gold"
LAYER_CHROME = "02_Chrome"
LAYER_COLLAR = "03_Collar"
LAYER_WOOD = "04_Wood"
LAYER_LENS = "05_Lens"
LAYER_SIGHT = "06_Sight"
LAYER_CONSTRUCTION = "00_Construction"
