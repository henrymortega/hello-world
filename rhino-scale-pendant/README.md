# Scale-lattice pendant (Rhino)

Parametric model of the hanging rounded-square metal pendant with a fading teardrop lattice.

This cloud session cannot drive your local Rhino (the RhinoAI MCP router is a Windows process that talks to a running Rhino). The files below are the model. Open them in Rhino 8 on the machine where RhinoAI is installed.

## Files

| File | What it is |
| --- | --- |
| `scale_pendant.py` | Rhino 8 Python builder — extrudes the body, cuts the lattice, adds the hanger |
| `scale_pendant.3dm` | Construction file: body solid, hole curves, hanger (no booleans) |
| `preview_front.png` | Front-view preview of the lattice |
| `params.py` | Dimensions in millimetres — edit this to change the design |

## Build it in Rhino

1. Open Rhino 8. Units: millimetres.
2. `ScriptEditor` → Open `scale_pendant.py` → Run.
   Alternative: `_RunPythonScript` and pick `scale_pendant.py`.
3. Optional: select the finished pendant and run `FilletEdge` at **0.8 mm** to round the cell rims.

To use RhinoAI / MCP from Cursor instead of the script: open Rhino, run `MCPConnect`, **reload Cursor**, and use a **local** agent (not a cloud agent). Then ask it to run `scale_pendant.py`.

## Default size

- Plate: 420 × 430 × 16 mm, corner radius 72 mm
- Lattice: 15 columns, brick-offset teardrop cells
- Fade: through-holes above ~30% height, shrinking pockets, then a solid bottom band
- Hanger: 12 mm sphere and 3.2 mm stem
