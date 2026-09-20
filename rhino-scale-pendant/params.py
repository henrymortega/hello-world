"""Shared parameters for the hanging scale-lattice pendant.

Units are millimeters. The silhouette is a rounded square plate with a
brick-pattern vesica/teardrop lattice that fades into solid metal at the
bottom, plus a spherical hanger at the top.
"""

# Overall body
WIDTH = 420.0
HEIGHT = 430.0
THICKNESS = 16.0
CORNER_RADIUS = 72.0

# Lattice — cell size is smaller than pitch so a metal web remains
COLS = 15
ROWS = 16
CELL_W = 23.2
CELL_H = 31.0
COL_PITCH = 30.0
ROW_PITCH = 24.8
SUPERELLIPSE_N = 1.72  # < 2 = more pointed teardrop/vesica
HOLE_FILLET = 0.8

# Fade: holes are full size above FADE_END, gone by FADE_START (0 = bottom, 1 = top)
FADE_START = 0.11
FADE_END = 0.30
BLIND_POCKET_BELOW = 0.24  # below this height, holes become shallow pockets

# Keep a solid band at the bottom and a smoother top edge
TOP_MARGIN = 42.0
BOTTOM_SOLID = 42.0
SIDE_OVERFLOW = 10.0  # allow holes to scallop the left/right edges

# Hardware
HANGER_SPHERE_R = 12.0
STEM_R = 3.2
STEM_H = 28.0

# Document
UNITS = "mm"
LAYER_BODY = "01_Body"
LAYER_LATTICE = "02_Lattice"
LAYER_POCKETS = "03_Pockets"
LAYER_HARDWARE = "04_Hardware"
LAYER_CONSTRUCTION = "00_Construction"
