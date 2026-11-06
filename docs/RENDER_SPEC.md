# RENDER_SPEC.md — Required render set

Renders are the only thing most people will ever see of your model. They are part of the
deliverable, not an afterthought. This spec is the single source of truth for what a compliant
render set looks like.

---

## 1. Hard requirements

| Parameter | Requirement |
| --- | --- |
| Count | **≥ 5** images in `renders/` (5–12 recommended), all also inside `renders.zip` |
| Resolution | **≥ 1600 × 1600** px, square. 2400 × 2400 preferred for hero assets |
| Format | PNG, 8-bit sRGB (16-bit acceptable). No JPEG for hero shots |
| Background | Opaque. Dark neutral (#1A1A1E–#26262B) or light neutral (#E8E8EA–#F2F2F2). **Not** transparent, **not** a checkerboard |
| Framing | Whole model in frame with **8–12 % margin** on all sides |
| Anti-aliasing | ≥ 64 samples or equivalent supersampling; no visible stair-stepping |
| Noise | Denoised or rendered clean; no fireflies, no salt-and-pepper |
| Colour management | AgX (Blender 4.x default) or ACES/Filmic. Correct view transform, no double gamma |
| File naming | `NN-kebab-description.png`, zero-padded, e.g. `01-hero-three-quarter.png` |
| Consistency | All shots share exposure, world lighting, and lens philosophy |

**Opaque background is mandatory** because transparent PNGs look broken in GitHub's dark/light themes
and in most grids. Give the model a floor and a backdrop; it costs nothing and looks professional.

---

## 2. Required views

Every package provides these six, in this order and with these names:

| # | Filename | What it must show |
| --- | --- | --- |
| 1 | `01-hero-three-quarter.png` | 3/4 front view, slight elevation (~10–20°), the "poster shot". Best lighting, most flattering angle. |
| 2 | `02-front.png` | Orthographic or near-ortho front view, level, whole model |
| 3 | `03-side.png` | Orthographic left side view, level, whole model |
| 4 | `04-back.png` | Rear view — proves there is no missing/unfinished side |
| 5 | `05-top.png` | Top (or bottom, if the underside is the interesting part) view |
| 6 | `06-detail-<feature>.png` | Macro/close-up of the most interesting feature (mechanism, texture, joinery, face) |

Optional but valued:

| # | Filename | What it shows |
| --- | --- | --- |
| 7 | `07-wireframe.png` | Same frame as hero, wireframe or matcap-over-wire. Proves topology quality |
| 8 | `08-scale-reference.png` | Shot with a 1 m grid floor or a human silhouette for scale |
| 9 | `09-context.png` | The asset in a simple environment, for environment/architecture categories |

Rename `06-detail-<feature>` to something concrete: `06-detail-hinge-mechanism.png`,
`06-detail-pommel-engraving.png`.

---

## 3. Camera guidelines

- **Lens:** 50–85 mm equivalent for props (avoids perspective distortion); 24–35 mm for architecture
  and environments. Do **not** use a wide angle on a product — it reads as a mistake.
- **Framing:** use the model's bounding box to compute framing, not eyeballing. Automate it (see
  WORKFLOW_BLENDER.md, which ships a framing helper).
- **Eye level / elevation:** hero 10–20° above the object's centre; orthographic views level with
  the object's centre unless the object is very tall.
- **Clipping:** far plane beyond the model, near plane close but not intersecting geometry. Check
  that no extremity (antenna, fingertip, roof ridge) is cut.
- **Orthographic views should actually be orthographic** (or ≥ 135 mm equivalent). Perspective
  "front" views look sloppy next to a proper ortho.
- Never render a view where a straight-on orientation is impossible — rotate the model, not the
  conventions.

---

## 4. Lighting guidelines

**Minimum: a three-point studio setup.**

| Light | Purpose | Typical intensity |
| --- | --- | --- |
| Key | main form definition, 35–50° off camera axis, above | strongest |
| Fill | lifts shadow side, opposite side, softer | 25–50 % of key |
| Rim / kicker | separates silhouette from background | 50–100 % of key, behind |
| World / HDRI | ambient bounce, colour | low, neutral, subtle gradient |

Rules:
- **No flat frontal single light.** If the render looks like a product photo of a flat-shaded
  primitive, the lighting failed.
- **Contact shadow required.** The object must sit on a floor with a visible, anchored shadow. No
  object floating in a void.
- **No blown highlights.** Check the histogram: highlights may reach 255 in tiny speculars, but not
  in large areas. No clipped base-colour regions.
- **No crushed blacks.** Deepest shadow should retain some detail unless a silhouette is intentional.
- **Emissive assets:** render one shot with the emission dominant (revealing falloff on nearby
  surfaces) and one with it off/subtle, so the geometry is still readable.
- **Consistency:** lock the world and light rig across the whole set. Only the camera moves.

---

## 5. Subject presentation

- **Clean the asset before rendering.** No studio rig visible in frame, no stray empties, no
  selection outlines, no viewport overlays, no axis gizmos.
- **Pose/arrangement:** the asset as it would be presented in a catalogue — upright, natural, or
  in a deliberate hero pose. No accidental tilt.
- **Level horizon:** the floor plane must be horizontal in level views. Don't ship renders where the
  object is tilted 2° for no reason.
- **Aspect:** square by default. Wide 16:9 only for environment/architecture sets, and then keep
  consistency within the set.

---

## 6. Self-inspection protocol (mandatory)

Before packaging, for each image ask:

1. **Is any part of the model cut off?** (zoom the corners — most clipping happens at extremities)
2. **Is the whole model lit well enough to read?** No black holes, no accidental fully-shadowed faces.
3. **Are there artefacts?** fireflies, banding, moire, z-fighting stripes, jagged edges, seam lines.
4. **Does the floor read as a floor?** Contact shadow present and plausible.
5. **Is the background clean?** No gradient banding, no visible world seams, no dead pixels.
6. **Does the material read as the material?** Metal looks metallic, glass looks refractive,
   painted surfaces have believable roughness.
7. **Would I put this in a portfolio?** If no, iterate.

Then build the contact sheet and inspect it as a whole:

```bash
python tools/make_render_sheet.py agent_<slug>/<package>
```

The sheet exposes inconsistent framing, mismatched exposure, and weak silhouettes that are easy to
miss one image at a time.

**Do not push renders you have not opened.** This is the single most common failure mode of
autonomous agents and it is grounds for rejection.

---

## 7. Reference rig (Blender)

```bash
bash tools/setup_blender.sh && source ~/.local/blender/activate.sh
blender -b model/<name>.blend --python tools/render_rig.py -- --res 1600 --samples 96 --out renders
```

[`tools/render_rig.py`](../tools/render_rig.py) produces the six required views, the wireframe pass and
the scale reference, all auto-framed from the asset's bounding box with the requested margin, and prints
a **framing check** (fails loudly on `CLIPPED`) plus a **black/flat/blown-highlight check**. Use it, or
reproduce its behaviour exactly in another renderer. Details and flags:
[`docs/WORKFLOW_BLENDER.md`](./WORKFLOW_BLENDER.md).

**You must paste the framing-check output into your run log / PR.** It is the evidence that the whole
model is in frame, which is the requirement most often violated.
