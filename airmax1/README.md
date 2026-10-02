# Nike Air Max 1 — Componentized Rhino Model (US 9 Left)

Parametric **block-out** of the Air Max 1 for V-Ray materialization in Rhino.

> **Scope:** This is a proportioned, layered starting model (last + panels + sole + Air unit), not a scanned or hand-sculpted product mesh. Use it to assign V-Ray materials and refine surfaces in Rhino.

## Deliverables

| File | Description |
|------|-------------|
| [`output/Nike_AirMax1_US9_Left.3dm`](output/Nike_AirMax1_US9_Left.3dm) | Rhino 8, mm, layered components |
| [`output/AirMax1_US9.blend`](output/AirMax1_US9.blend) | Blender source (subdiv pipeline) |
| [`output/renders/`](output/renders/) | Preview renders |
| [`references/retail/`](references/retail/) | Nike FZ5808-102 multi-angle photos |

## Rebuild

```bash
# Organic mesh (Blender)
blender --background --python airmax1/scripts/blender_build_am1.py
python airmax1/scripts/pack_3dm.py

# Or lighter parametric path
python airmax1/scripts/build_airmax1.py
```

## Layers → V-Ray

- `01_Sole` — rubber outsole + waffle  
- `02_Midsole` — foam (Air window booleaned in Blender source)  
- `03_AirUnit` — clear window / membrane / pillars  
- `04_Upper` — mesh last + collar  
- `05_Overlays` — mudguard, suede, swoosh  
- `06_Hardware` — eyelets / lace locks  
- `07_SoftGoods` — tongue / laces / insole  

## References

Nike DNA mudguard notes (7 mm mid / 15–17 mm heel), Nike.com construction, SNS FZ5808-102 gallery, lab stack/width figures.
