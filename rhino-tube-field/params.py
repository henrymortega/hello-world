"""Parameters for the green tube-field dissolving into striped waves.

Units: millimetres.
"""

# Grid
COLS = 50
ROWS = 42
PITCH = 15.0
TUBE_OUTER_R = 5.5
TUBE_INNER_R = 4.35
MAX_HEIGHT = 54.0
MIN_HEIGHT = 1.8
DOT_HEIGHT = 2.2  # leftover specks in the fade

# Wave surface
WAVE_AMP = 64.0
WAVE_PERIODS = 4.6
WAVE_SLANT = 0.22  # mix of X into the wave axis
WAVE_X_START = 0.40  # fraction of field width where waves begin
WAVE_OVERHANG = 80.0  # extra mm past the tube field on the right
WAVE_NU = 28
WAVE_NV = 22

# Materials
GREEN = (36, 158, 78, 255)
GREEN_DARK = (18, 92, 46, 255)
WHITE = (245, 245, 248, 255)
BLACK = (18, 18, 20, 255)

# Layers
LAYER_GROUND = "01_Ground"
LAYER_TUBES = "02_Tubes"
LAYER_DOTS = "03_FadeDots"
LAYER_WAVES = "04_Waves"
LAYER_STRIPES = "05_Stripes"
LAYER_CONSTRUCTION = "00_Construction"
