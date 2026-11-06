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

## 4. Render rig: world, lights, cameras

Full script — save as `tools_render/render_set.py` inside your workspace and run headless.
It builds a neutral studio, six cameras auto-framed to the asset's bounding box, and renders the
required set.

```python
"""Render the compliant render set for an asset.
Usage: blender -b model/asset.blend --python render_set.py -- --res 2400 --samples 128
"""
import bpy, sys, math, os
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(flag, default):
    return type(default)(argv[argv.index(flag) + 1]) if flag in argv else default

RES     = arg("--res", 2400)
SAMPLES = arg("--samples", 128)
OUT     = arg("--out", os.path.abspath("renders"))
MARGIN  = arg("--margin", 0.10)          # 10% empty border
os.makedirs(OUT, exist_ok=True)

scene = bpy.context.scene

# ---------- render settings ----------
scene.render.engine = 'CYCLES'
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.render.resolution_x = RES
scene.render.resolution_y = RES
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.image_settings.color_depth = '8'
scene.view_settings.view_transform = 'AgX'      # 'ACES' / 'Filmic' also fine

# ---------- world ----------
world = bpy.data.worlds.new("studio_world")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.055, 0.055, 0.062, 1)   # dark neutral, not pure black
bg.inputs[1].default_value = 0.35

# ---------- floor + backdrop ----------
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
floor = bpy.context.object
floor.name = "rig_floor"
floor.data.materials.append(pbr("rig_floor_mat", (0.20, 0.20, 0.21), 0.55, 0.0))

# ---------- three-point lights ----------
def area(name, loc, energy, size, color=(1, 1, 1)):
    d = bpy.data.lights.new(name, 'AREA')
    d.energy = energy; d.size = size; d.color = color
    o = bpy.data.objects.new(name, d)
    bpy.context.collection.objects.link(o)
    o.location = loc
    # aim at origin
    direction = Vector((0, 0, 0)) - o.location
    o.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    return o

KEY  = area("rig_key",  (2.6, -3.2, 3.6), 900, 3.0, (1.00, 0.97, 0.92))
FILL = area("rig_fill", (-3.4, -2.2, 1.6), 260, 4.0, (0.92, 0.95, 1.00))
RIM  = area("rig_rim",  (-1.4, 3.8, 2.8), 700, 2.5, (0.98, 0.99, 1.00))

# ---------- asset bounds ----------
meshes = [o for o in bpy.context.scene.objects
          if o.type == 'MESH' and not o.name.startswith("rig_")]
coords = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
mn = Vector((min(c.x for c in coords), min(c.y for c in coords), min(c.z for c in coords)))
mx = Vector((max(c.x for c in coords), max(c.y for c in coords), max(c.z for c in coords)))
center = (mn + mx) / 2
size   = (mx - mn)
radius = max(size) / 2 * (1 + MARGIN)

# ---------- camera helper ----------
def make_cam(name, direction, lens=70, ortho=False, scale=1.0):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    if ortho:
        cam_data.type = 'ORTHO'
        cam_data.ortho_scale = max(size) * (1 + 2 * MARGIN) * scale
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.collection.objects.link(cam)
    d = Vector(direction).normalized()
    dist = (max(size) * 1.15) / math.tan(math.radians(cam_data.angle / 2)) if not ortho else 10.0
    cam.location = center + d * max(dist, max(size) * 2.2)
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    return cam

cams = {
  "01-hero-three-quarter": make_cam("cam_hero",   ( 0.85, -1.00,  0.42), lens=70),
  "02-front":              make_cam("cam_front",  ( 0.00, -1.00,  0.00), ortho=True),
  "03-side":               make_cam("cam_side",   (-1.00,  0.00,  0.00), ortho=True),
  "04-back":               make_cam("cam_back",   ( 0.00,  1.00,  0.00), ortho=True),
  "05-top":                make_cam("cam_top",    ( 0.00, -0.05,  1.00), ortho=True),
  "06-detail":             make_cam("cam_detail", ( 0.60, -0.80,  0.30), lens=100),
}

# tighten the detail cam to the upper third / most interesting area
detail_target = Vector((center.x, center.y, mn.z + size.z * 0.72))
cam_d = cams["06-detail"]
cam_d.location = detail_target + Vector((0.45, -0.70, 0.25)) * max(size)
cam_d.rotation_euler = (detail_target - cam_d.location).to_track_quat('-Z', 'Y').to_euler()
cam_d.data.lens = 110

# ---------- render ----------
for name, cam in cams.items():
    scene.camera = cam
    scene.render.filepath = os.path.join(OUT, f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print("wrote", scene.render.filepath)

# ---------- optional wireframe pass ----------
for o in meshes:
    m = bpy.data.materials.new("wire_tmp")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    wire = nt.nodes.new("ShaderNodeWireframe"); wire.inputs[0].default_value = 0.0
    emis = nt.nodes.new("ShaderNodeEmission"); emis.inputs[0].default_value = (0.05, 0.35, 0.6, 1)
    out  = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(wire.outputs[0], emis.inputs[0])
    nt.links.new(emis.outputs[0], out.inputs[0])
    o.data.materials.clear(); o.data.materials.append(m)
scene.camera = cams["01-hero-three-quarter"]
scene.render.filepath = os.path.join(OUT, "07-wireframe.png")
bpy.ops.render.render(write_still=True)
```

Notes
- `~128` samples with denoising is usually clean enough at 2400². Raise it if you see fireflies.
- If the asset is emissive, run a second pass with emission strength scaled down.
- For "floating" assets (aircraft, drones) put a subtle floor far below and let the contact shadow be
  soft — but still present, so the composition is grounded.

---

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
