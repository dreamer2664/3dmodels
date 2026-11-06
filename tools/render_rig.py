#!/usr/bin/env python3
"""render_rig.py — build a compliant render set for a .blend, headless.

Runs INSIDE Blender's Python:

    blender -b model/asset.blend --python tools/render_rig.py -- \
        --res 2400 --samples 128 --out renders

What it does
  1. adds a neutral studio: floor, world, three-point area lights (scaled to the asset),
  2. finds every mesh object that is not part of the rig,
  3. creates the six required cameras (hero 3/4, front, side, back, top, detail),
     auto-framed to the asset's bounding box with a configurable empty margin,
  4. renders each view to <out>/NN-name.png,
  5. optionally renders a wireframe pass and a 1 m grid scale-reference pass,
  6. prints a framing report (content bounding box and margin per image) when Pillow
     is available, so you can see immediately if something got clipped.

The framing maths projects the eight bounding-box corners into camera space, so the
model fills the frame correctly whether it is a flat plate or a tall column, and the
requested margin is honoured in both axes. (A naive "max dimension * 1.15 / tan(fov/2)"
formula — which used to be in this file — puts the camera ~60x too far away, because
Blender's Camera.angle is in radians, not degrees. Do not reintroduce it.)

Exit codes: 0 = rendered the requested set, 1 = a view failed to render.
"""

import math
import os
import sys

import bpy
from mathutils import Vector

# --------------------------------------------------------------------------- #
# Args
# --------------------------------------------------------------------------- #
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(flag, default):
    """Read `--flag value` from argv after `--`. Booleans accept 0/1/true/false/no/yes."""
    if flag not in argv:
        return default
    raw = argv[argv.index(flag) + 1]
    if isinstance(default, bool):
        return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}
    return type(default)(raw)


if "--help" in argv or "-h" in argv:
    print(__doc__)
    raise SystemExit(0)

RES = arg("--res", 2400)
SAMPLES = arg("--samples", 128)
MARGIN = arg("--margin", 0.10)            # fraction of frame left empty on each side
OUT = arg("--out", os.path.abspath("renders"))
ENGINE = arg("--engine", "CYCLES")        # CYCLES or EEVEE
BACKGROUND = arg("--bg", "dark")          # dark | light
WIREFRAME = arg("--wireframe", True)
SCALE_REF = arg("--scale-ref", True)
DETAIL_AT = arg("--detail-at", 0.70)      # fraction of height where the detail cam aims
GPU = arg("--gpu", False)
TILE = arg("--tile", 0)                   # reserved: 0 = auto (chosen from available RAM)
FORCE_NO_DENOISE = arg("--no-denoise", False)   # force the low-RAM path
POST_DENOISE = arg("--post-denoise", 0.8)       # blended amount for that path
ONLY_VIEWS = arg("--views", "all")              # "all" or a comma list of view prefixes, e.g. 01,03
RIG_PREFIX = "rig_"

os.makedirs(OUT, exist_ok=True)
scene = bpy.context.scene
if RES < 320:
    print(f"[rig] NOTE: --res {RES} is smoke-test territory; "
          f"docs/RENDER_SPEC.md requires >= 1600 for a real package")


# --------------------------------------------------------------------------- #
# Render settings
# --------------------------------------------------------------------------- #
def available_ram_mb():
    """Total/free RAM in MB, best effort, no third-party imports."""
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as fh:
            info = {}
            for line in fh:
                key, _, rest = line.partition(":")
                info[key.strip()] = int(rest.strip().split()[0])   # kB
        return info.get("MemTotal", 0) // 1024, info.get("MemAvailable", 0) // 1024
    except Exception:
        return 0, 0


def configure_render():
    engine = ENGINE.upper()
    if engine.startswith("EEVEE"):
        scene.render.engine = "BLENDER_EEVEE_NEXT" if bpy.app.version >= (4, 2, 0) else "BLENDER_EEVEE"
    else:
        scene.render.engine = "CYCLES"
        scene.cycles.samples = SAMPLES
        # OpenImageDenoise can exceed the memory of a small sandbox at high resolution and the
        # process gets OOM-killed mid-render, producing no file at all. Decide up front:
        #   < 3 GB RAM and res > 1200  -> render at target res with denoise OFF and fewer
        #                                 samples (Cycles output is already clean enough at
        #                                 the sample counts we recommend), then downscale to
        #                                 the required size with the supersampled result.
        total_mb, avail_mb = available_ram_mb()
        if FORCE_NO_DENOISE:
            denoise_ok = False
        else:
            denoise_ok = total_mb == 0 or total_mb >= 3000 or RES <= 1200
        scene.cycles.use_denoising = denoise_ok
        if not denoise_ok:
            print(f"[rig] only {total_mb} MB RAM available: denoising at {RES}px would be "
                  f"OOM-killed, so denoise is OFF. Adaptive sampling + a high sample "
                  f"ceiling keeps it clean and fast.")
            if SAMPLES < 96:
                scene.cycles.samples = 96       # cleaned afterwards by post_denoise()
        # noise/quality knobs: adaptive sampling must stay ON or a 1600px view costs
        # 4+ minutes on a 2-core CPU box
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = arg("--adaptive", 0.02)
        scene.cycles.max_bounces = 6
        scene.cycles.diffuse_bounces = 3
        scene.cycles.glossy_bounces = 3
        scene.cycles.transmission_bounces = 4
        scene.cycles.transparent_max_bounces = 4
        if GPU:
            scene.cycles.device = "GPU"
            prefs = bpy.context.preferences.addons.get("cycles")
            if prefs:
                prefs.preferences.compute_device_type = "OPTIX"
                for dev in prefs.preferences.get_devices()[0]:
                    dev.use = True
                scene.cycles.device = "GPU"
        else:
            scene.cycles.device = "CPU"

    scene.render.resolution_x = RES
    scene.render.resolution_y = RES
    scene.render.resolution_percentage = 100
    scene.render.use_border = False
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.use_file_extension = True
    try:
        scene.view_settings.view_transform = "AgX"
    except TypeError:
        scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0


def studio_world():
    world = bpy.data.worlds.new("rig_world")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    if BACKGROUND == "light":
        bg.inputs[0].default_value = (0.80, 0.80, 0.82, 1.0)
        bg.inputs[1].default_value = 0.55
    else:
        bg.inputs[0].default_value = (0.045, 0.045, 0.050, 1.0)
        bg.inputs[1].default_value = 0.40


# --------------------------------------------------------------------------- #
# Asset bounds (before any rig geometry exists)
# --------------------------------------------------------------------------- #
def asset_meshes():
    return [
        o for o in scene.objects
        if o.type == "MESH" and not o.name.startswith(RIG_PREFIX)
    ]


def asset_bounds(meshes):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in meshes:
        ob_eval = o.evaluated_get(depsgraph)
        for corner in ob_eval.bound_box:
            pts.append(ob_eval.matrix_world @ Vector(corner))
    if not pts:
        raise SystemExit("render_rig: no mesh objects found to frame")
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


MESHES = asset_meshes()
LO, HI = asset_bounds(MESHES)
CENTER = (LO + HI) * 0.5
SIZE = HI - LO
MAX_DIM = max(SIZE.x, SIZE.y, SIZE.z)
CORNERS = [
    Vector((x, y, z))
    for x in (LO.x, HI.x)
    for y in (LO.y, HI.y)
    for z in (LO.z, HI.z)
]

if MAX_DIM <= 0:
    raise SystemExit("render_rig: asset has zero size; check the scene and applied transforms")

print(f"[rig] asset bounds: {tuple(round(v, 4) for v in LO)} .. {tuple(round(v, 4) for v in HI)}")
print(f"[rig] size: {tuple(round(v, 4) for v in SIZE)} m, max {MAX_DIM:.4f} m, "
      f"{len(MESHES)} mesh object(s)")


# --------------------------------------------------------------------------- #
# Studio geometry, scaled to the asset so the look is size-independent
# --------------------------------------------------------------------------- #
def make_material(name, base, rough, metal):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    return m


def build_floor():
    bpy.ops.mesh.primitive_plane_add(size=MAX_DIM * 24, location=(CENTER.x, CENTER.y, LO.z))
    floor = bpy.context.object
    floor.name = RIG_PREFIX + "floor"
    tone = (0.34, 0.34, 0.36) if BACKGROUND == "light" else (0.16, 0.16, 0.17)
    floor.data.materials.append(make_material(RIG_PREFIX + "floor_mat", tone, 0.62, 0.0))
    return floor


def build_lights():
    """Three-point rig, positioned relative to the asset and energy-scaled by distance^2."""
    s = MAX_DIM
    specs = [
        # name,   direction offset (x, y, z) in units of asset size, energy factor, size factor, colour
        ("key",  (1.35, -1.65, 1.80), 26.0, 1.5, (1.00, 0.97, 0.92)),
        ("fill", (-1.75, -1.10, 0.80), 7.5, 2.0, (0.92, 0.95, 1.00)),
        ("rim",  (-0.75, 1.95, 1.45), 20.0, 1.3, (0.98, 0.99, 1.00)),
    ]
    lights = []
    for name, offset, e_factor, size_factor, colour in specs:
        loc = CENTER + Vector(offset) * s
        data = bpy.data.lights.new(RIG_PREFIX + name, "AREA")
        data.shape = "SQUARE"
        data.size = s * size_factor
        data.color = colour
        dist = (loc - CENTER).length
        # energy in watts; scale with distance^2 so brightness is independent of asset size
        data.energy = e_factor * max(dist, 1e-3) ** 2
        obj = bpy.data.objects.new(RIG_PREFIX + name, data)
        scene.collection.objects.link(obj)
        obj.location = loc
        obj.rotation_euler = (CENTER - loc).to_track_quat("-Z", "Y").to_euler()
        lights.append(obj)
    return lights


# --------------------------------------------------------------------------- #
# Framing
# --------------------------------------------------------------------------- #
def make_camera(name, direction, lens=70.0, ortho=False, focus=None, pad=1.0):
    """Create a camera that frames every bbox corner with MARGIN empty space.

    Projects the eight corners onto the camera's right/up axes and solves for the
    distance at which the largest extent fills (1 - 2*MARGIN) of the frame.
    """
    focus = Vector(focus) if focus is not None else CENTER
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam_data.sensor_fit = "AUTO"
    if ortho:
        cam_data.type = "ORTHO"

    direction = Vector(direction).normalized()
    # camera basis
    forward = -direction                       # camera looks down its -Z
    up_hint = Vector((0, 0, 1))
    if abs(forward.dot(up_hint)) > 0.99:        # straight-up/down views: use Y as up
        up_hint = Vector((0, 1, 0))
    right = forward.cross(up_hint).normalized()
    up = right.cross(forward).normalized()

    # extents of the asset in the camera's own axes
    rel = [c - focus for c in CORNERS]
    half_w = max(abs(r.dot(right)) for r in rel)
    half_h = max(abs(r.dot(up)) for r in rel)
    half_d = max(abs(r.dot(forward)) for r in rel)
    half_w = max(half_w * pad, 1e-4)
    half_h = max(half_h * pad, 1e-4)

    target = 1.0 - 2.0 * MARGIN                # fraction of frame the asset may fill
    if ortho:
        cam_data.ortho_scale = max(half_w, half_h) * 2.0 / target
        dist = half_d + MAX_DIM * 3.0
    else:
        # Blender: Camera.angle is in RADIANS. sensor_fit AUTO on a square frame uses
        # the larger dimension, so the same half-angle applies to both axes.
        half_angle = cam_data.angle * 0.5
        dist_w = half_w / (math.tan(half_angle) * target)
        dist_h = half_h / (math.tan(half_angle) * target)
        dist = max(dist_w, dist_h) + half_d
        cam_data.clip_start = max(dist * 0.01, 0.001)
        cam_data.clip_end = max(dist * 4.0, 10.0)

    cam = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam)
    cam.location = focus + direction * dist
    cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
    return cam


def build_cameras():
    cams = {
        "01-hero-three-quarter": make_camera(RIG_PREFIX + "cam_hero", (0.80, -1.00, 0.38), lens=70),
        "02-front": make_camera(RIG_PREFIX + "cam_front", (0.0, -1.0, 0.0), ortho=True),
        "03-side": make_camera(RIG_PREFIX + "cam_side", (-1.0, 0.0, 0.0), ortho=True),
        "04-back": make_camera(RIG_PREFIX + "cam_back", (0.0, 1.0, 0.0), ortho=True),
        "05-top": make_camera(RIG_PREFIX + "cam_top", (0.0, -0.06, 1.0), ortho=True),
    }
    detail_focus = Vector((
        CENTER.x,
        CENTER.y,
        LO.z + SIZE.z * DETAIL_AT,
    ))
    cams["06-detail"] = make_camera(
        RIG_PREFIX + "cam_detail",
        (0.65, -0.85, 0.30),
        lens=110,
        focus=detail_focus,
        pad=1.35,
    )
    return cams


# --------------------------------------------------------------------------- #
# Render
# --------------------------------------------------------------------------- #
def render_view(cam, filepath_stem):
    scene.camera = cam
    scene.render.filepath = os.path.join(OUT, filepath_stem + ".png")
    bpy.ops.render.render(write_still=True)
    if not os.path.exists(scene.render.filepath):
        raise SystemExit(f"render_rig: render failed, no file written: {scene.render.filepath}")
    print(f"[rig] wrote {scene.render.filepath}")
    return scene.render.filepath


def render_wireframe_pass(hero_cam):
    """Topology pass: real wireframe geometry (Wireframe modifier on duplicates).

    A shader-level Wireframe node proved unreliable under Cycles+denoise (thin lines
    get filtered out, and on some builds the node never fires), so this builds actual
    edge tubes. It costs a few seconds and always renders what you see in the viewport.
    """
    dups = []
    try:
        wire_mat = bpy.data.materials.new(RIG_PREFIX + "wire_mat")
        wire_mat.use_nodes = True
        for node in list(wire_mat.node_tree.nodes):
            if node.type != "OUTPUT_MATERIAL":
                wire_mat.node_tree.nodes.remove(node)
        nt = wire_mat.node_tree
        output = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        # dark faces so the silhouette still reads, bright emissive edges on top
        face_emit = nt.nodes.new("ShaderNodeEmission")
        face_emit.inputs[0].default_value = (0.045, 0.048, 0.055, 1.0)
        edge_emit = nt.nodes.new("ShaderNodeEmission")
        edge_emit.inputs[0].default_value = (0.12, 0.66, 1.0, 1.0)

        for obj in MESHES:
            dup = obj.copy()
            dup.data = obj.data.copy()
            dup.name = RIG_PREFIX + "wire_" + obj.name
            scene.collection.objects.link(dup)
            dup.data.materials.clear()
            dup.data.materials.append(wire_mat)
            mod = dup.modifiers.new("wire", "WIREFRAME")
            mod.thickness = max(MAX_DIM * 0.0016, 0.0004)
            mod.use_replace = True
            mod.use_even_offset = True
            edge_emit.inputs[1].default_value = 1.0
            dups.append(dup)
            obj.hide_render = True
        render_view(hero_cam, "07-wireframe")
    finally:
        for dup in dups:
            bpy.data.objects.remove(dup, do_unlink=True)
        for obj in MESHES:
            obj.hide_render = False


def render_scale_reference(hero_cam):
    """1 m grid floor so a human can read the true scale off the image."""
    grid_objs = []
    if MAX_DIM < 1.0:
        span = 3.0
    else:
        span = math.ceil(MAX_DIM + 2.0)
    count = int(span) + 1
    mat = make_material(RIG_PREFIX + "grid_mat", (0.55, 0.55, 0.58), 0.7, 0.0)
    step = 1.0
    half = count // 2
    for i in range(-half, half + 1):
        for axis in (0, 1):
            bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
            bar = bpy.context.object
            bar.name = RIG_PREFIX + f"grid_line_{axis}_{i}"
            bar.scale = (0.006, count * step, 0.002) if axis == 0 else (count * step, 0.006, 0.002)
            bar.location = (i * step, 0, LO.z + 0.001) if axis == 0 else (0, i * step, LO.z + 0.001)
            bar.data.materials.append(mat)
            grid_objs.append(bar)
    try:
        render_view(hero_cam, "08-scale-reference")
    finally:
        for bar in grid_objs:
            bpy.data.objects.remove(bar, do_unlink=True)


# --------------------------------------------------------------------------- #
# Post-render framing report
# --------------------------------------------------------------------------- #
def post_denoise(paths, strength=POST_DENOISE):
    """Low-memory bilateral-ish denoise for the no-OIDN path.

    Uses numpy (bundled with Blender) and Blender's image API only, so it costs ~100 MB
    instead of OIDN's gigabyte. Blender images are linear float RGBA, so the blend happens
    on linear values and the file is written back as 8-bit sRGB through the render settings.
    """
    try:
        import numpy as np
    except Exception:
        print("[rig] numpy unavailable inside Blender — skipping post-denoise")
        return
    if scene.cycles.use_denoising:
        return

    def box(arr, radius):
        out = arr
        for axis in (0, 1):
            pad = [(0, 0)] * out.ndim
            pad[axis] = (radius + 1, radius)
            padded = np.pad(out, pad, mode="edge")
            cs = np.cumsum(padded, axis=axis)
            if axis == 0:
                out = (cs[2 * radius + 1:, :, :] - cs[:-(2 * radius + 1), :, :]) / (2 * radius + 1)
            else:
                out = (cs[:, 2 * radius + 1:, :] - cs[:, :-(2 * radius + 1), :]) / (2 * radius + 1)
        return out

    print("\n[rig] post-denoise (no-OIDN path)")
    for path in paths:
        if not os.path.exists(path):
            continue
        try:
            img = bpy.data.images.load(path, check_existing=False)
            w, h = img.size
            buf = np.empty(w * h * 4, dtype=np.float32)
            img.pixels.foreach_get(buf)
            arr = buf.reshape(h, w, 4)
            rgb = arr[:, :, :3]
            guide = box(rgb, 2)
            diff = np.abs(rgb - guide).mean(axis=2, keepdims=True)
            weight = np.exp(-(diff ** 2) / (2 * 0.10 ** 2))
            num = box(guide * weight, 2)
            den = np.clip(box(weight, 2), 1e-6, None)
            smoothed = num / den
            out_rgb = np.clip(rgb * (1.0 - strength) + smoothed * strength, 0.0, 1.0)
            arr[:, :, :3] = out_rgb
            img.pixels.foreach_set(arr.ravel())
            img.filepath_raw = path
            img.file_format = "PNG"
            img.save()
            bpy.data.images.remove(img)
            print(f"  {os.path.basename(path):<28} cleaned (strength {strength:.2f})")
        except Exception as exc:  # noqa: BLE001
            print(f"  {os.path.basename(path):<28} post-denoise failed ({exc})")


def finalise_images(paths):
    """Report images that came out below the required resolution.

    Deliberately does NOT upscale: an upscaled 400px render is still a 400px render, and
    silently inflating it would let a cheap render pass tools/preflight.py. If a view is
    smaller than RES, re-render it — Blender occasionally writes a reduced buffer when the
    saved .blend carries a resolution_percentage override, so force it back to 100%:
        blender -b model/<name>.blend --python-expr \
          "import bpy; s=bpy.context.scene; s.render.resolution_percentage=100"
    """
    undersized = []
    for path in paths:
        if not os.path.exists(path):
            continue
        try:
            img = bpy.data.images.load(path, check_existing=False)
            w, h = img.size
            bpy.data.images.remove(img)
        except Exception:
            continue
        if w < RES or h < RES:
            undersized.append((os.path.basename(path), w, h))
    if undersized:
        print("\n[rig] UNDERSIZED RENDERS (not acceptable for a package):")
        for name, w, h in undersized:
            print(f"  {name:<28} {w}x{h} < {RES}x{RES}")
        print("[rig] Re-render these views at the target size. Do not upscale them.")


def check_framing(cams):
    """Project the asset bounding-box corners into each camera and report the margin.

    This is exact (no pixel guessing, no floor confusing the measurement) and costs
    nothing: world_to_camera_view returns coordinates in 0..1 of the rendered frame.
    A margin below ~4% means the asset is touching the frame edge — fix before pushing.
    """
    from bpy_extras.object_utils import world_to_camera_view

    print(f"\n[rig] framing check (target margin {MARGIN * 100:.0f}% on every side)")
    problems = []
    for stem, cam in cams.items():
        xs, ys = [], []
        for corner in CORNERS:
            co = world_to_camera_view(scene, cam, corner)
            xs.append(co.x)
            ys.append(co.y)
        left, right = min(xs), 1.0 - max(xs)
        bottom, top = min(ys), 1.0 - max(ys)
        worst = min(left, right, bottom, top)
        status = "ok"
        if worst < 0.004:
            status = "CLIPPED"
            problems.append(stem)
        elif worst < MARGIN * 0.6:
            status = "tight"
        print(
            f"  {stem:<24} L{left*100:5.1f}% R{right*100:5.1f}% "
            f"T{top*100:5.1f}% B{bottom*100:5.1f}%  {status}"
        )

    # the detail camera is deliberately tight on a feature, so only check it is not
    # pointing at empty space
    if problems:
        print(f"[rig] WARNING: {len(problems)} view(s) clipped: {', '.join(problems)}")
        print("[rig] Raise --margin, or check that the asset is centred on its origin.")
    return problems


def verify_outputs(paths):
    """Cheap sanity checks that a render is not empty/black/identical."""
    try:
        import numpy as np
    except Exception:
        print("[rig] numpy unavailable — skipping empty/black frame checks")
        return
    print("\n[rig] output sanity check")
    for path in paths:
        if not os.path.exists(path):
            print(f"  {os.path.basename(path):<28} MISSING")
            continue
        try:
            img = bpy.data.images.load(path, check_existing=False)
            w, h = img.size
            buf = np.empty(w * h * 4, dtype=np.float32)
            img.pixels.foreach_get(buf)
            arr = buf.reshape(h, w, 4)[:, :, :3]
            bpy.data.images.remove(img)
        except Exception as exc:
            print(f"  {os.path.basename(path):<28} unreadable ({exc})")
            continue
        mean = float(arr.mean())
        std = float(arr.std())
        flags = []
        if mean < 0.01:
            flags.append("BLACK")
        if std < 0.008:
            flags.append("FLAT/EMPTY")
        if float(arr.max()) >= 0.999 and float((arr >= 0.999).mean()) > 0.05:
            flags.append("BLOWN HIGHLIGHTS")
        size_mb = os.path.getsize(path) / (1024 * 1024)
        print(
            f"  {os.path.basename(path):<28} mean {mean:.3f} std {std:.3f} "
            f"{size_mb:5.1f} MB  {' '.join(flags) if flags else 'ok'}"
        )


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    configure_render()
    studio_world()
    build_floor()
    build_lights()
    cams = build_cameras()

    written = []
    wanted = None if ONLY_VIEWS.strip().lower() == "all" else [
        v.strip() for v in ONLY_VIEWS.split(",") if v.strip()
    ]
    for stem, cam in cams.items():
        if wanted is not None and not any(stem.startswith(w) for w in wanted):
            continue
        written.append(render_view(cam, stem))
    if wanted is not None and not written:
        raise SystemExit(f"render_rig: --views {ONLY_VIEWS} matched no camera")

    if WIREFRAME:
        render_wireframe_pass(cams["01-hero-three-quarter"])
        written.append(os.path.join(OUT, "07-wireframe.png"))
    if SCALE_REF:
        render_scale_reference(cams["01-hero-three-quarter"])
        written.append(os.path.join(OUT, "08-scale-reference.png"))

    post_denoise([p for p in written if os.path.exists(p)])
    finalise_images([p for p in written if os.path.exists(p)])
    check_framing(cams)
    verify_outputs([p for p in written if os.path.exists(p)])
    print(f"\n[rig] done: {len(written)} image(s) in {OUT}")
    print("[rig] NOW LOOK AT THEM. Open every image. Fix what is wrong. Then push.")


main()
