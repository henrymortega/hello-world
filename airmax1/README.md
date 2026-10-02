# Nike Air Max 1 — Componentized Rhino Model

Men's **US 9 Left** Air Max 1 as a Rhino `.3dm` (mm), organized for **V-Ray** materialization.

## Output

| File | Description |
|------|-------------|
| [`output/Nike_AirMax1_US9_Left.3dm`](output/Nike_AirMax1_US9_Left.3dm) | Componentized Rhino 8 model |
| [`output/preview_airmax1.png`](output/preview_airmax1.png) | Quick geometry preview |
| [`scripts/build_airmax1.py`](scripts/build_airmax1.py) | Parametric rebuild script |

## Rebuild

```bash
pip install rhino3dm numpy
python airmax1/scripts/build_airmax1.py
```

## Research basis

- **Nike DNA / nike.com** — visible Max Air cutaway (Pompidou-inspired), mudguard heights from archive notes (**7 mm** midfoot, **15–17 mm** heel), mesh + suede + synthetic upper, waffle outsole, lace-lock guidance.
- **Product construction (Air Max 1 Essential)** — foam midsole + heel Max Air, rubber waffle outsole, padded low collar.
- **Lab scale (men’s)** — heel stack **32.2 mm**, forefoot **20.1 mm**, drop **~12.1 mm**, midsole widths **~81.8 / 107.9 mm**.

## Layer map (assign V-Ray here)

| Layer | Typical V-Ray material |
|-------|------------------------|
| `01_Sole::*` | Black rubber (+ red accent wraps) |
| `02_Midsole::Foam_Body` | Matte phylon/foam (soft SSS optional) |
| `03_AirUnit::Window` | Clear TPU, IOR ≈ 1.49, refraction |
| `03_AirUnit::Membrane` / `Pillars` | Translucent air-bag internals |
| `04_Upper::*` | Engineered mesh / collar textile |
| `05_Overlays::Mudguard` | Synthetic leather (black) |
| `05_Overlays::Quarter_Suede` / `Heel_*` | Bone/grey suede |
| `05_Overlays::Swoosh` | Synthetic overlay |
| `06_Hardware::*` | Dark plastic |
| `07_SoftGoods::*` | Lace / tongue / sockliner |

Named materials (`MAT_*`) are embedded with user-string **VRayHint** notes. Object materials are set from object (not layer), so you can remap per piece.

## Groups

`GRP_Outsole`, `GRP_Midsole`, `GRP_AirUnit`, `GRP_Upper`, `GRP_Overlays`, `GRP_Hardware`, `GRP_SoftGoods`

## Coordinate system

- Origin at heel contact on ground  
- **+X** toe · **+Y** lateral (left shoe) · **+Z** up · units **mm**

## V-Ray workflow tips

1. Open the `.3dm` in Rhino with V-Ray.
2. Hide `00_Reference` when rendering.
3. Replace each `MAT_*` with a V-Ray material (keep clear refraction on `AirUnit_Window`).
4. Add weave/opacity maps on mesh layers; suede sheen/bump on overlays.
5. Optional: Boolean the air window against the midsole in Rhino for a true cutaway.

## Scope note

This is a **parametric, componentized blocking model** scaled to published AM1 proportions and Nike construction breakdown—not a scanned last or tooling-ready surface model. Use it to materialize and refine in Rhino/V-Ray.
