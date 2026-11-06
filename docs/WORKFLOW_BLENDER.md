# WORKFLOW_BLENDER.md — Headless modelling + render recipe

A practical, copy-pasteable workflow for producing a compliant package with Blender 4.x from the
command line. Adapt to your environment; the *output* is what's judged, not the tool.

If Blender is not available, reproduce this behaviour with any headless renderer (three.js +
headless Chrome, Filament, Pyrender, etc.) and say so in the README.

---

## 1. Invocation basics

```bash
# version check
blender --version

# run a python script headless on an empty scene
blender --background --factory-startup --python build_model.py

# open a .blend and run a script against it
blender --background model/asset.blend --python render_set.py -- --res 2400
```

`--factory-startup` gives you a predictable environment (no user add-ons, no startup cube).
Pass custom args after `--` and read them with `sys.argv`.

---

## 2. Scene hygiene rules (do these from the first line of your script)

```python
import bpy

# unit system: metric, metres
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
scene.unit_settings.length_unit = 'METERS'

# start clean
bpy.ops.wm.read_factory_settings(use_empty=True)   # if not using --factory-startup
```

- Delete default cube/camera/light if present.
- Keep the asset in a collection named after the model; keep the render rig (cameras, lights, floor)
  in a separate collection named `_render_rig` and exclude it from the `.glb` export.
- Apply transforms before export:
  ```python
  bpy.ops.object.select_all(action='SELECT')
  bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
  ```
- Recalculate normals outside on manifold solids:
  ```python
  bpy.ops.object.mode_set(mode='EDIT')
  bpy.ops.mesh.select_all(action='SELECT')
  bpy.ops.mesh.normals_make_consistent(inside=False)
  bpy.ops.object.mode_set(mode='OBJECT')
  ```
- Merge by distance 0.0001 m, then delete loose geometry.
- Origin at the ground-centre of the bounding box:
  ```python
  bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
  ob = bpy.context.object
  # then move so min Z == 0 and X/Y centre == 0
  ```
  A simple scripted helper: compute world-space bbox over all mesh objects, translate the parent
  empty so the bbox centre sits at X=Y=0 and bbox min Z = 0.

---

## 3. Materials — safe PBR defaults

```python
def pbr(name, base, rough, metal, aniso=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if "Anisotropic" in bsdf.inputs:
        bsdf.inputs["Anisotropic"].default_value = aniso
    return m

# sRGB-ish colour constants (linearise if you feed these into shader sockets)
PAINT_CREAM   = (0.62, 0.60, 0.55)
BRASS         = (0.87, 0.66, 0.32)
STEEL_BRUSHED = (0.56, 0.57, 0.58)
GLASS_SMOKED  = (0.55, 0.58, 0.55)
RUBBER        = (0.045, 0.045, 0.05)
```

Rules of thumb (from STANDARDS.md):
- metallic surfaces: `Metallic = 1.0`, base colour = metal reflectance, roughness 0.1–0.4
- paints: `Metallic = 0`, roughness 0.35–0.6
- rubber/fabric: roughness 0.75–0.95
- glass: transmission instead of alpha where the renderer supports it; roughness < 0.1
- never base colour (1,1,1) or (0,0,0)

Name materials by purpose: `paint_enamel_cream`, `metal_brass_brushed`, `glass_clear_smoked`.

---

## 4. Render rig: use the shipped, tested one

Do not hand-roll the camera maths. [`tools/setup_blender.sh`](../tools/setup_blender.sh) installs
Blender; [`tools/render_rig.py`](../tools/render_rig.py) builds the studio and renders the compliant
set:

```bash
source ~/.local/blender/activate.sh
blender -b model/<name>.blend --python tools/render_rig.py -- \
    --res 1600 --samples 96 --out renders
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--res` | 2400 | square resolution in px (must be ≥ 1600) |
| `--samples` | 128 | Cycles samples (96 is clean with denoise) |
| `--margin` | 0.10 | empty border around the asset, per side |
| `--engine` | CYCLES | `CYCLES` (CPU, works headless) — EEVEE fails without a GPU surface |
| `--bg` | dark | `dark` or `light` neutral backdrop |
| `--wireframe` | true | also render `07-wireframe.png` |
| `--scale-ref` | true | also render `08-scale-reference.png` with a 1 m grid |
| `--detail-at` | 0.70 | height fraction the detail camera aims at |
| `--views` | `all` | render a subset, e.g. `--views 01,02` (batch rendering when memory is tight) |
| `--no-denoise` | false | force the low-RAM path (OIDN off, built-in post-denoise on) |
| `--post-denoise` | 0.8 | blend amount for that post-denoise |
| `--adaptive` | 0.02 | adaptive sampling threshold (lower = cleaner, slower) |
| `--gpu` | false | use OptiX if a GPU is really available |

It writes `renders/01-hero-three-quarter.png` … `06-detail.png`, plus the optional 07/08 passes, and
then prints **two checks you must read**:

```
[rig] framing check (target margin 10% on every side)
  02-front                 L 28.9% R 28.9% T 10.0% B 10.0%  ok
  05-top                   L  0.0% R  0.0% T  0.0% B  0.0%  CLIPPED   <- fix before pushing
[rig] output sanity check
  03-side.png   mean 0.216 std 0.191   ok        <- BLACK / FLAT-EMPTY / BLOWN HIGHLIGHTS flag artefacts
```

**Memory note:** on machines with < 3 GB RAM, OpenImageDenoise gets OOM-killed at ≥ 1400 px and the
render silently produces no file. The rig detects available RAM, turns OIDN off and post-denoises
instead (`--no-denoise` forces this). If `blender` exits 137, that was the cause — batch views with
`--views` and keep `--no-denoise`.

The framing check projects the asset's bounding-box corners into each camera with
`world_to_camera_view`, so it is exact — it cannot be fooled by the floor or the backdrop. If a view
reports `CLIPPED`, raise `--margin` or check that the asset is centred on its origin.

### Why the rig avoids two classic traps

1. **`Camera.angle` is in radians, not degrees.** The common
   `dist = max_dim * 1.15 / tan(radians(camera.angle / 2))` formula converts twice and puts the
   camera ~60× too far away — the "model looks like a distant speck" render. Always use the returned
   value directly (`camera.angle * 0.5`) or solve from the bounding box as the rig does.
2. **Compute the bounds before you add studio geometry.** Build the floor/lights *after* reading the
   asset bounds (and exclude rig objects by name) or the camera framing will include the backdrop.

### If you write your own rig

It must produce the same six views, the same margin, and its own framing/sanity checks. The output is
what is judged — but a rig that silently renders the floor instead of the model is worse than no rig,
so verify by opening the first image before you render the other five.

### Optional passes

- **Wireframe:** `render_rig.py` duplicates the meshes, applies a Wireframe modifier (real geometry,
  not a shader node — the shader `Wireframe` node is silently filtered out under Cycles + denoise) and
  renders dark faces with emissive edges.
- **Scale reference:** a 1 m grid is laid on the floor so a viewer can read the true size; it is
  removed immediately afterwards.
- **Emissive assets:** run a second pass with emission strength reduced so the geometry stays readable
  (see `docs/RENDER_SPEC.md` §4).

## 5. Export the shippable `.glb`

```python
import bpy

# select only the asset (exclude the _render_rig collection)
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
    if o.type == 'MESH' and not o.name.startswith("rig_"):
        o.select_set(True)

bpy.ops.export_scene.gltf(
    filepath="model/asset.glb",
    export_format='GLB',
    use_selection=True,
    export_yup=True,              # glTF standard: +Y up, -Z forward
    export_apply=True,            # apply modifiers
    export_texcoords=True,
    export_normals=True,
    export_materials='EXPORT',
    export_image_format='AUTO',   # embeds textures in the GLB
    export_cameras=False,
    export_lights=False,
)
```

Then **verify by re-importing**:
```bash
blender --background --factory-startup --python-expr "
import bpy; bpy.ops.import_scene.gltf(filepath='model/asset.glb');
print('objects:', len(bpy.data.objects), 'tris:', sum(len(o.data.loop_triangles) if o.data.loop_triangles else 0 for o in bpy.data.objects if o.type=='MESH'))"
```

And run the repo checker:
```bash
python tools/check_glb.py agent_<slug>/<package>/model/<package>.glb
```

---

## 6. Scale sanity check

Before you finish, drop a 1 m reference cube next to your model and render one frame. If your coffee
mug is the size of a fridge, you'll see it immediately. Then delete the reference cube.

Alternatively, keep a `08-scale-reference.png` render with a 1 m grid floor — encouraged by
RENDER_SPEC.md.

---

## 7. Common pitfalls

| Symptom | Cause | Fix |
| --- | --- | --- |
| Model invisible in render | camera inside mesh / normals flipped / objects hidden | check bounds + `normals_make_consistent` |
| Model looks tiny in frame | camera framing by eyeball | use bbox-driven framing (§4) |
| Blown-out white areas | base colour 1,1,1 or over-bright area lights | lower light energy, darken base colour |
| Noisy render | too few samples | ≥ 128 + denoise, or increase resolution and downscale |
| Banded background | 8-bit gradient | add slight film grain or dither, or lighter noise |
| z-fighting stripes | coplanar surfaces | offset ≥ 0.2 mm |
| Glass renders black | transmission without proper IOR/background | set IOR 1.45–1.52, ensure lit environment behind |
| `.glb` looks different from render | non-PBR node groups dropped on export | stick to Principled BSDF |
| Huge `.glb` | unapplied subsurf or 4K textures | apply/decimate, downscale maps to 1–2K |
