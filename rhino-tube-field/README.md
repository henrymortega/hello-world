# Tube field → silk waves (Rhino)

Parametric model of a grid of hollow green tubes whose height and density fade into a rolling black-and-white wave surface.

## Files

| File | What it is |
| --- | --- |
| `tube_field.3dm` | Open this in Rhino — tubes, wave surface, shaded mesh |
| `tube_field.py` | Rhino 8 script that rebuilds the solids |
| `preview.png` | Bird's-eye preview |
| `params.py` | Grid, pipe, and wave dimensions (mm) |

## In Rhino 8

1. Open `tube_field.3dm`, or run `tube_field.py` from ScriptEditor.
2. Select the wave surface (`04_Waves`) and run `_Zebra` to get the silk-fold stripes from the reference.
3. The tubes already use a green glass-style colour. In Rendered / Raytraced, raise transparency if you want them more like acrylic.

## Defaults

- 50 × 42 grid, 15 mm pitch, 5.5 mm outer radius (hollow)
- Height field with a dense left “continent”, winding gaps, and a fade to specks
- Wave surface on the right, ~64 mm amplitude
