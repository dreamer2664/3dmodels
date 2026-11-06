<!--
HOW TO USE THIS TEMPLATE
1. Copy it to agent_YOURSLUG/PACKAGENAME/README.md
2. Fill the front-matter block below with real values (run tools/check_glb.py for the
   triangle count and the bounding-box dimensions).
3. Replace every angle-bracket placeholder and every italic prompt in the body.
4. Delete this comment.
5. status must be "released" before you push: a pushed package is a finished package.
   tools/preflight.py rejects "draft" status, unfinished-package wording, leftover
   placeholders, missing sections, and a renders.zip older than the newest render.
-->

---
model: <package-name>
package: <package-name>
workspace: <agent_slug>
category: <hard-surface-prop | architecture | organic | vehicle | environment | stylised | product-viz>
version: 1.0.0
status: released
author_agent: <agent_slug>
created: <YYYY-MM-DD>
license: CC-BY-4.0
dimensions_m: {x: <0.000>, y: <0.000>, z: <0.000>}
triangles: <0>
vertices: <0>
objects: <0>
materials: <0>
textures: <0 or none>
formats: [glb, blend]
render_count: <0>
render_min_resolution: <1600>
software: [<Blender 4.2>, <Cycles>]
brief: "<brief id or 'none'>"
brief_source: owner            # owner | pack | agent | prompt  (where the subject came from)
---

# <Model Name>

<One sentence: what this is, plainly. e.g. "A portable brass oil lantern, 31 cm tall,
with a hinged vent cap and a wire bail handle.">

![Hero three-quarter view](renders/01-hero-three-quarter.png)

---

## What this model depicts

<3–6 substantive paragraphs. Cover identity, form, parts, materials, surface/wear, and
what it is NOT (stylised? fictional? reconstruction?). Measurements over adjectives.>

<Paragraph 1 — identity: what the object is, what it is for, period/context if relevant.>

<Paragraph 2 — form: overall shape, proportions, defining features, how it is assembled.>

<Paragraph 3 — parts: enumerate every notable sub-part and what it does. This is the
section a reader will use to understand your model without opening it.>

<Paragraph 4 — materials: what each part is made of in reality, and the material you used.>

<Paragraph 5 — surface & wear: finish, patina, dirt, paint condition, any signage or marks.>

<Paragraph 6 — the honest framing: "This is a <realistic reconstruction / stylised
interpretation> based on <type of reference>. It is not a scan or a replica of a
specific surviving object.">

---

## Dimensions and scale

| Dimension | Value |
| --- | --- |
| Width (X) | <0.00> m |
| Depth (Y) | <0.00> m |
| Height (Z) | <0.00> m |
| Ground footprint | <0.00 × 0.00> m |

Real-world metric scale. Origin at the centre of the base; the model sits on Z = 0 (Blender) /
Y = 0 (glTF). Up-axis +Y on export.

---

## Technical sheet

| Property | Value |
| --- | --- |
| Category | `<hard-surface-prop / architecture / organic / vehicle / environment / stylised / product-viz>` |
| Triangles | <00000> |
| Vertices | <00000> |
| Objects | <0> (parented under `<asset_name>` empty) |
| Materials | <0> |
| Textures | <0 — list resolutions, or "none (procedural)"> |
| UV layout | <single UV set, no overlaps / mirrored and declared / not required> |
| Formats | `.glb`, `.blend` |
| File sizes | `.glb` <0.0> MB, `.blend` <0.0> MB |
| Renders | <0> images, <1600>×<1600> px |
| Toolchain | <Blender 4.2, Cycles, 128 samples, AgX> |
| LODs | <none / LOD0–LOD3> |
| Rig / animation | <none / describe> |

---

## Materials

| Material | Type | Base colour | Roughness | Metalness | Used on |
| --- | --- | --- | --- | --- | --- |
| `paint_enamel_<colour>` | PBR MR | `#RRGGBB` | 0.00 | 0.00 | <parts> |
| `metal_<metal>_<finish>` | PBR MR | `#RRGGBB` | 0.00 | 1.00 | <parts> |
| `glass_<tint>` | PBR MR + transmission | `#RRGGBB` | 0.00 | 0.00 | <parts> |
| `rubber_black` | PBR MR | `#RRGGBB` | 0.00 | 0.00 | <parts> |

<One line on how materials were authored: procedurally with node graphs / baked from
procedural sources / hand-painted maps.>

---

## Render set

| # | View | File |
| --- | --- | --- |
| 1 | Hero three-quarter | `renders/01-hero-three-quarter.png` |
| 2 | Front | `renders/02-front.png` |
| 3 | Side | `renders/03-side.png` |
| 4 | Back | `renders/04-back.png` |
| 5 | Top | `renders/05-top.png` |
| 6 | Detail — <feature> | `renders/06-detail-<feature>.png` |
| 7 | Wireframe (optional) | `renders/07-wireframe.png` |

![Front view](renders/02-front.png)
![Side view](renders/03-side.png)
![Back view](renders/04-back.png)
![Top view](renders/05-top.png)
![Detail — <feature>](renders/06-detail-<feature>.png)

All renders: <1600>×<1600> px, Cycles <128> samples, AgX view transform, three-point studio
lighting, neutral dark backdrop.

---

## Usage notes

- **Blender:** `File > Import > glTF 2.0`, or open `model/<package>.blend` directly.
- **Re-rendering the set:** `blender -b model/<package>.blend --python tools/render_rig.py -- --res 1600 --samples 96 --out renders`
  (run `bash tools/setup_blender.sh` first — see docs/SETUP.md).
- **Engines:** game-ready mesh; single material set; <no LODs / LODs included>. Scale factor 1.0,
  metres, +Y up.
- **Pivots:** parent empty `<asset_name>` at the ground centre; rotate the parent to place the asset.
- **Transparency:** `<glass material uses alpha blend — ensure the material is in the transparent
  render queue in Unity/Unreal>` (delete this line if not applicable).
- **Print suitability:** <not checked for printing / watertight and suitable for printing at 1:1>.

---

## Limitations & known issues

- <e.g. Interior of the <part> is simplified; not intended for extreme close-ups inside the shell.>
- <e.g. Procedural materials only — no baked texture set, so appearance may differ in engines with
  limited shader support.>
- <e.g. No LODs or collision mesh included.>
- <e.g. <Sub-part> is modelled as a single shell rather than as separate physical pieces.>

<If you could not meet any requirement in STANDARDS.md, say which and why, here.>

---

## Self-review

- [ ] Real-world metric scale, origin at ground centre, transforms applied
- [ ] Manifold, no ngons on curved surfaces, consistent normals, no z-fighting
- [ ] Bevels on hard edges; deliberate, uniform density
- [ ] All materials PBR with plausible values; no pure white/black
- [ ] ≥ 5 renders ≥ 1600×1600; full model in frame with margin; no clipping
- [ ] Three-point lighting; contact shadow present; no blown highlights or noise
- [ ] **Every render opened and inspected; contact sheet inspected**
- [ ] `renders.zip` mirrors `renders/`, opens cleanly, under 80 MB
- [ ] `.glb` re-imported and verified against the renders
- [ ] README complete; no placeholders; limitations are honest
- [ ] `python tools/preflight.py agent_<slug>` exits 0

---

## Licence & credits

- Geometry authored from scratch for this repository; no third-party mesh data used.
- <Authoring note: "modelled in Blender 4.2 from reference photographs described in NOTES.md".>
- External assets: <none / CC0 HDRI from Poly Haven — credited here>.
- Licence: **CC BY 4.0** (see repository [LICENSE](../../../LICENSE)).
