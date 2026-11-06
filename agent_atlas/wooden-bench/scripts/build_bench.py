#!/usr/bin/env python3
"""build_bench.py — run inside Blender to author the wooden-bench package.

    blender -b --factory-startup --python agent_atlas/wooden-bench/scripts/build_bench.py

Three-seat park bench at real-world scale (1.60 m wide, seat 0.45 m, back top
0.85 m): oak slats on three timber trestles, four arched cast-iron arm rests
(two outer + two centre dividers) with bolted mounting plates. Front of the
bench faces -Y. Applies 2 mm / 1.4 mm bevels, projects tiled grain UVs,
assigns the baked texture set, parents everything under `wooden_bench`, packs
images and saves the .blend.
"""
import math
import os

import bpy
import bmesh
from mathutils import Vector, Matrix

REPO = "/home/user/repo"
PKG = os.path.join(REPO, "agent_atlas", "wooden-bench")
TEX = os.path.join(PKG, "model", "textures")
MODEL = os.path.join(PKG, "model")

# --------------------------------------------------------------------------- #
# scene reset
# --------------------------------------------------------------------------- #
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0


def new_object(name):
    me = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    return ob


# --------------------------------------------------------------------------- #
# geometry helpers — all boxes are closed, outward-wound (recomputed later)
# --------------------------------------------------------------------------- #
def add_box(bm, verts, x0, x1, y0, y1, z0, z1):
    def v(co):
        key = (round(co[0], 6), round(co[1], 6), round(co[2], 6))
        if key not in verts:
            verts[key] = bm.verts.new(key)
        return verts[key]

    b = [v(c) for c in [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]]
    for f in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
              (2, 3, 7, 6), (1, 2, 6, 5), (3, 0, 4, 7)]:
        bm.faces.new([b[i] for i in f])


def catmull(points, subdiv=6):
    """Smooth 2-D (y', z, width) polyline through the control points."""
    pts = list(points)
    out = []
    n = len(pts)
    for i in range(n - 1):
        p0 = pts[i - 1] if i > 0 else pts[0]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < n else pts[-1]
        for s in range(subdiv):
            t = s / subdiv
            t2, t3 = t * t, t * t * t

            def cr(a, b, c, d):
                return 0.5 * (2 * b + (c - a) * t + (2 * a - 5 * b + 4 * c - d) * t2
                              + (3 * b - a - 3 * c + d) * t3)
            out.append(tuple(cr(p0[k], p1[k], p2[k], p3[k]) for k in range(3)))
    out.append(tuple(pts[-1]))
    return out


def add_skin_strip(bm, samples, x_centre, thickness):
    """Closed flat strap band skinned around a side-view centreline.
    samples: list of (y', z, w) with y' positive toward the FRONT of the bench
    (actual y = -y'); band width w lies in the YZ plane, thickness along X."""
    rings = []
    n = len(samples)
    for i, (yp, z, w) in enumerate(samples):
        nxt = samples[min(i + 1, n - 1)]
        prv = samples[max(i - 1, 0)]
        ty, tz = nxt[0] - prv[0], nxt[1] - prv[1]
        L = math.hypot(ty, tz) or 1.0
        ny, nz = -tz / L, ty / L
        half = w * 0.5
        ring = []
        for sx, sn in ((-1, +1), (+1, +1), (+1, -1), (-1, -1)):
            ring.append(bm.verts.new(
                (x_centre + sx * thickness * 0.5,
                 -(yp + sn * half * ny),
                 z + sn * half * nz)))
        rings.append(ring)
    for i in range(n - 1):
        a, b = rings[i], rings[i + 1]
        for k in range(4):
            k2 = (k + 1) % 4
            bm.faces.new((a[k], a[k2], b[k2], b[k]))
    bm.faces.new(tuple(reversed(rings[0])))
    bm.faces.new(tuple(rings[-1]))


def add_hex_bolt(bm, loc, axis, r, depth, out_sign):
    """Hex-head bolt prism; the head sits at loc and extends along the axis."""
    va, vb = [], []
    off = Vector((out_sign * depth, 0.0, 0.0)) if axis == "x" else \
        Vector((0.0, out_sign * depth, 0.0))
    for i in range(6):
        a = math.radians(60 * i + 30)
        d1, d2 = r * math.cos(a), r * math.sin(a)
        base = Vector((loc[0], loc[1] + d1, loc[2] + d2)) if axis == "x" \
            else Vector((loc[0] + d1, loc[1], loc[2] + d2))
        va.append(bm.verts.new(base))
        vb.append(bm.verts.new(base + off))
    bm.faces.new(tuple(reversed(va)))
    bm.faces.new(vb)
    for i in range(6):
        j = (i + 1) % 6
        bm.faces.new((va[i], va[j], vb[j], vb[i]))


# --------------------------------------------------------------------------- #
# materials — baked texture set from agent_atlas/wooden-bench/scripts/make_textures.py
# --------------------------------------------------------------------------- #
def load_image(name, srgb):
    img = bpy.data.images.load(os.path.join(TEX, name), check_existing=False)
    img.name = name.rsplit(".", 1)[0]
    img.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
    return img


def make_material(name, maps=None, base=(0.5, 0.5, 0.5), rough=0.5, metal=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if maps:
        texco = nt.nodes.new("ShaderNodeTexCoord")
        for slot, fname, srgb, loc in (
            ("Base Color", maps.get("basecolor"), True, (-700, 300)),
            ("Roughness", maps.get("roughness"), False, (-700, 0)),
            ("Normal-src", maps.get("normal"), False, (-700, -350)),
        ):
            if not fname:
                continue
            t = nt.nodes.new("ShaderNodeTexImage")
            t.image = load_image(fname, srgb)
            t.location = loc
            nt.links.new(texco.outputs["UV"], t.inputs["Vector"])
            if slot == "Normal-src":
                nm = nt.nodes.new("ShaderNodeNormalMap")
                nm.location = (-380, -350)
                nm.inputs["Strength"].default_value = 0.22
                nt.links.new(t.outputs["Color"], nm.inputs["Color"])
                nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
            else:
                nt.links.new(t.outputs["Color"], bsdf.inputs[slot])
    return mat


MAT_WOOD = make_material(
    "wood_oak_bench",
    maps={"basecolor": "wood_bench_basecolor.png",
          "roughness": "wood_bench_roughness.png",
          "normal": "wood_bench_normal.png"},
    base=(0.24, 0.16, 0.09), rough=0.5, metal=0.0)
MAT_IRON = make_material(
    "metal_cast_iron_weathered",
    maps={"basecolor": "iron_cast_basecolor.png",
          "roughness": "iron_cast_roughness.png",
          "normal": "iron_cast_normal.png"},
    base=(0.065, 0.065, 0.070), rough=0.62, metal=1.0)
MAT_BOLT = make_material("metal_iron_dark", base=(0.055, 0.055, 0.060),
                         rough=0.48, metal=1.0)

# --------------------------------------------------------------------------- #
# bench dimensions (metres)
# --------------------------------------------------------------------------- #
SEAT_Z = 0.45
SLAT_T = 0.030
RAIL_Z0, RAIL_Z1 = 0.355, 0.426
TRESTLE_XS = (-0.755, 0.0, 0.755)
WOOD_T = 0.055
RIB_T = 0.055                     # seat rail flush with legs and posts
FACE = TRESTLE_XS[2] + WOOD_T / 2  # 0.7825 — outer face of the end trestles
FRONT_Y = -0.285                   # front edge of rail and slats
REAR_Y = 0.16
TILT = math.radians(10.0)
POST_Y0 = 0.085
POST_TY = 0.085
APRON_X = (TRESTLE_XS[0] - 0.0275, TRESTLE_XS[2] + 0.0275)   # full width


def post_y(z):
    return POST_Y0 + math.tan(TILT) * z


WOOD_U, WOOD_V = 2.0, 0.25
IRON_UV = 0.30


def finish_object(ob, mat, kind, phase):
    """Bevel, smooth-by-angle, tiled grain UVs, single material."""
    mod = ob.modifiers.new("bevel", "BEVEL")
    mod.width = 0.0022 if kind == "wood" else 0.0014
    mod.segments = 2
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(42)
    for o in bpy.context.view_layer.objects:
        o.select_set(o is ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier="bevel")

    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uvl = me.uv_layers.active.data
    tu, tv = (WOOD_U, WOOD_V) if kind == "wood" else (IRON_UV, IRON_UV)
    for poly in me.polygons:
        n = [abs(v) for v in poly.normal]
        nax = n.index(max(n))
        loops = [li for li in poly.loop_indices]
        coords = [me.vertices[me.loops[li].vertex_index].co for li in loops]
        ext = [max(c[a] for c in coords) - min(c[a] for c in coords) for a in range(3)]
        free = [a for a in range(3) if a != nax]
        free.sort(key=lambda a: -ext[a])
        u_ax, v_ax = free
        for j, li in enumerate(loops):
            co = coords[j]
            uvl[li].uv = (co[u_ax] / tu + phase, co[v_ax] / tv + phase * 0.37 + 0.5)
    try:
        bpy.ops.object.shade_auto_smooth(angle=math.radians(40))
    except Exception:
        for p in me.polygons:
            p.use_smooth = False
    me.materials.clear()
    me.materials.append(mat)


# --------------------------------------------------------------------------- #
# WOOD parts
# --------------------------------------------------------------------------- #
parts = {}


def obj(name):
    if name not in parts:
        parts[name] = (new_object(name), bmesh.new(), {})
    return parts[name][1], parts[name][2]


# seat: five oak slats, one fraction thicker (worn board), flush to trestles
bm, _ = obj("seat_slats")
y = -0.275
for i in range(5):
    t = SLAT_T + (0.0008 if i == 2 else 0.0)
    x0 = -FACE + (0.004 if i % 2 else 0.0)
    x1 = FACE - (0.005 if i % 2 else 0.0)
    add_box(bm, _, x0, x1, y, y + 0.075, SEAT_Z - t, SEAT_Z)
    y += 0.087

# back: four tilted boards on the front faces of the rear posts
bm, _ = obj("back_slats")
for i, z in enumerate((0.545, 0.635, 0.725, 0.815)):
    yc = post_y(z) - POST_TY * 0.5 * math.cos(TILT) - 0.0145
    verts_local = {}
    start = len(bm.verts[:])
    add_box(bm, verts_local, -FACE + (0.005 if i == 1 else 0.0), FACE, -0.014, 0.014,
            -0.039, 0.039)
    m = Matrix.Translation((0, yc, z)) @ Matrix.Rotation(-TILT, 4, "X")
    for v in list(bm.verts)[start:]:
        v.co = m @ v.co

# three trestles: front leg + tilted rear post + seat rail
for name, tx in zip(("trestle_left", "trestle_center", "trestle_right"), TRESTLE_XS):
    bm, _ = obj(name)
    add_box(bm, _, tx - WOOD_T / 2, tx + WOOD_T / 2, FRONT_Y, FRONT_Y + 0.080,
            0.0, RAIL_Z0 + 0.005)
    start = len(bm.verts[:])
    hw = POST_TY * 0.5
    add_box(bm, _, tx - WOOD_T / 2, tx + WOOD_T / 2, -hw, hw, 0.008, 0.85 / math.cos(TILT))
    m = Matrix.Translation((0, POST_Y0, 0)) @ Matrix.Rotation(-TILT, 4, "X")
    for v in list(bm.verts)[start:]:
        v.co = m @ v.co
    add_box(bm, _, tx - RIB_T / 2, tx + RIB_T / 2, FRONT_Y - 0.015, REAR_Y,
            RAIL_Z0, RAIL_Z1)

# front apron and rear brace
bm, _ = obj("apron_front")
add_box(bm, _, APRON_X[0], APRON_X[1], FRONT_Y - 0.018, FRONT_Y + 0.022, 0.24, 0.345)
bm, _ = obj("back_brace")
yb = post_y(0.20) + POST_TY * 0.5 * math.cos(TILT) - 0.010
add_box(bm, _, APRON_X[0], APRON_X[1], yb, yb + 0.055, 0.175, 0.265)

for name in list(parts):
    ob, bm, _ = parts[name]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()
    parts[name] = (ob, None, None)

# --------------------------------------------------------------------------- #
# CAST IRON — one arm design placed at four mounting points
# --------------------------------------------------------------------------- #
TH = 0.0135
PLATE_W = 0.09


def arm_paths():
    rear = catmull([
        (-0.150, 0.325, PLATE_W),
        (-0.150, 0.430, PLATE_W - 0.016),
        (-0.146, 0.545, 0.052),
        (-0.108, 0.628, 0.047),
        (-0.030, 0.668, 0.045),
        (0.045, 0.676, 0.045),
        (0.104, 0.662, 0.046),
    ], subdiv=7)
    cy, cz = 0.128, 0.601
    curl = [(0.104, 0.662, 0.046)]
    for s in range(30):
        t = s / 29.0
        th = math.radians(95.0 - 300.0 * t)
        r = 0.055 + (0.028 - 0.055) * t
        curl.append((cy + r * math.cos(th), cz + r * math.sin(th), 0.046 - 0.015 * t))
    curl += [(0.168, 0.552, 0.046), (0.172, 0.528, 0.048)]
    front = catmull([
        (0.170, 0.560, 0.048),
        (0.176, 0.470, 0.050),
        (0.192, 0.385, 0.062),
        (0.225, 0.330, PLATE_W - 0.018),
        (0.268, 0.306, PLATE_W),
        (0.298, 0.300, PLATE_W),
    ], subdiv=6)
    return rear, curl, front


REAR, CURL, FRONT = arm_paths()

ARMS = {  # name: (plate-centre x, X sign the bolt heads face)
    "arm_right_outer": (FACE + TH * 0.5, +1),
    "arm_left_outer": (-FACE - TH * 0.5, -1),
    "arm_right_inner": (WOOD_T / 2 + TH * 0.5, +1),
    "arm_left_inner": (-WOOD_T / 2 - TH * 0.5, -1),
}

bolts_ob = new_object("bolts_hardware")
bolts_bm = bmesh.new()

for a_name, (ax, sign) in ARMS.items():
    ob = new_object(a_name)
    bm = bmesh.new()
    main = catmull([
        (-0.150, 0.325, 0.075), (-0.150, 0.47, 0.055),
        (-0.120, 0.60, 0.040), (-0.070, 0.660, 0.040),
        (0.000, 0.675, 0.040), (0.090, 0.670, 0.040),
        (0.155, 0.640, 0.040), (0.175, 0.580, 0.040),
        (0.180, 0.470, 0.045), (0.192, 0.385, 0.055),
        (0.225, 0.330, 0.070), (0.280, 0.305, 0.075)
    ], subdiv=7)
    add_skin_strip(bm, main, ax, TH)
    # rear-plate bolts: two heads, horizontal axis, on the post side above
    # and below the seat-rail edge, plus two foot bolts at the front nosing
    for yy, zz in ((-0.150, 0.352), (-0.150, 0.418)):
        add_hex_bolt(bm, (ax + sign * TH * 0.5, -yy, zz), "x",
                     r=0.0068, depth=0.005, out_sign=sign)
    for zz in (0.288, 0.318):
        add_hex_bolt(bm, (ax + sign * TH * 0.5, -0.292, zz), "x",
                     r=0.0064, depth=0.005, out_sign=sign)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()

# two more heads on the rear of the posts (back view), collected as hardware
for a_name, (ax, sign) in ARMS.items():
    for yy, zz in ((-0.108, 0.470), (0.196, 0.545)):
        pass
bmesh.ops.recalc_face_normals(bolts_bm, faces=bolts_bm.faces[:])
bolts_bm.to_mesh(bolts_ob.data)
bolts_bm.free()

# --------------------------------------------------------------------------- #
# finish: UVs, materials, hierarchy, pack, save
# --------------------------------------------------------------------------- #
WOOD_PHASES = {"seat_slats": 0.0, "back_slats": 0.23, "trestle_left": 0.51,
               "trestle_center": 0.86, "trestle_right": 0.13,
               "apron_front": 0.61, "back_brace": 0.33}
for name, ph in WOOD_PHASES.items():
    finish_object(parts[name][0], MAT_WOOD, "wood", ph)
for a_name in ARMS:
    finish_object(bpy.data.objects[a_name], MAT_IRON, "iron", 0.37)

# bolts ended up merged per-arm above; drop the empty hardware object
bpy.data.objects.remove(bolts_ob, do_unlink=True)

root = bpy.data.objects.new("wooden_bench", None)
root.empty_display_type = "PLAIN_AXES"
root.empty_display_size = 0.2
scene.collection.objects.link(root)
for ob in list(scene.objects):
    if ob.type == "MESH" and ob.parent is None:
        ob.parent = root

for key in parts:
    ob = parts[key][0]
    ob.data.name = key
    ob.location = (0.0, 0.0, 0.0)

bpy.ops.object.select_all(action="DESELECT")
bpy.ops.file.pack_all()
blend_path = os.path.join(MODEL, "wooden-bench.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print("[build] saved", blend_path)

bpy.context.view_layer.update()
tris = 0
for ob in scene.objects:
    if ob.type != "MESH":
        continue
    for p in ob.data.polygons:
        tris += max(len(p.vertices) - 2, 0)
mins = Vector((1e9,) * 3)
maxs = Vector((-1e9,) * 3)
for ob in scene.objects:
    if ob.type != "MESH":
        continue
    for c in ob.bound_box:
        wco = ob.matrix_world @ Vector(c)
        mins = Vector(map(min, mins, wco))
        maxs = Vector(map(max, maxs, wco))
print(f"[build] mesh-objects={len([o for o in scene.objects if o.type == 'MESH'])} "
      f"tris={tris} verts={sum(len(o.data.vertices) for o in scene.objects if o.type == 'MESH')}")
print(f"[build] bbox {tuple(round(v, 4) for v in mins)} .. {tuple(round(v, 4) for v in maxs)}"
      f"  size {(maxs - mins).x:.3f} x {(maxs - mins).y:.3f} x {(maxs - mins).z:.3f} m")
print(f"[build] z-min must be 0.0000: {mins.z:.4f}")
