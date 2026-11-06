# EXAMPLE — a fully filled package README

> **This is an illustrative reference, not a real package.** It exists so that an agent can see
> exactly what "complete and honest" looks like before writing its own. Do not copy the numbers or
> the asset — copy the *structure, depth, and tone*. The real template is
> [`templates/01_MODEL_README_TEMPLATE.md`](../templates/01_MODEL_README_TEMPLATE.md) and the
> content contract is [`docs/MODEL_SPEC.md`](./MODEL_SPEC.md).

---

```yaml
---
model: brass-portable-lantern
package: brass-portable-lantern
workspace: agent_atlas
category: hard-surface-prop
version: 1.0.0
status: released
author_agent: agent_atlas
created: 2026-11-06
license: CC-BY-4.0
dimensions_m: {x: 0.162, y: 0.162, z: 0.312}
triangles: 48210
vertices: 24980
objects: 7
materials: 6
textures: 5
formats: [glb, blend]
render_count: 7
render_min_resolution: 2000
software: [Blender 4.2, Cycles]
---
```

# Brass Portable Lantern

A 31 cm kerosene hand lantern: pressed brass body, domed vent cap, hinged side door, wire bail
handle and a clear glass globe, finished with light handling wear and a warm patina in the crevices.

![Hero three-quarter view](renders/01-hero-three-quarter.png)

---

## What this model depicts

This is a portable oil (kerosene) hand lantern of the type carried by railway workers, farmhands and
night watchmen from roughly 1880 to 1950. It is a *generic reconstruction of a widely manufactured
class of object* rather than a replica of one specific surviving lantern: the proportions, the burner
topology and the bail attachment follow the common late-19th-century pattern, while the exact
stamping and maker's mark are invented.

The object is a vertically oriented cylinder: a 16 cm flared base reservoir tapering into a narrower
collar, above which sits the glass globe, capped by a domed vent with a small lifting bail on top.
Total height is 31.2 cm, of which 9 cm is the reservoir, 12.6 cm the glass, and 9.6 cm the vent
assembly and handle arc. The heavy base reads as the densest mass; the glass is the visual void; the
brass cap closes the silhouette with a single clean dome. Everything is aligned on one vertical axis,
which is what makes the object instantly recognisable at thumbnail size.

The parts are: the **base reservoir**, a spun-brass cup with a rolled bottom seam, a filler neck with
a captive knurled cap on the left side, and a machined wick-adjuster shaft with a fluted brass knob on
the right; the **burner assembly**, a short collar with four air vents and a lift lever for the wick;
the **glass globe**, a slightly bulged cylinder with a fire-polished top lip, seated on a cork gasket;
the **four vertical guard wires**, tensioned between the base collar and the vent, which protect the
glass; the **side door** on the left, hinged at the base collar, which opens to light the wick; the
**vent cap**, a pressed dome with louvred slots around the rim and a small loop on top; and the
**bail handle**, a 2.5 mm drawn-brass wire arc that swings on two riveted pivots in the vent cap
ears. Each of these is a separate object in the file, parented to a single empty.

In the real object, the body, cap, collar and handle are brass; the wick adjuster is brass with a
steel spindle; the globe is soda-lime glass; the seal under the globe is cork; the gasket in the
filler cap is leather. In the model, brass is a single metallic-roughness material with a patina
mask, the steel spindle is a separate brushed-metal material, and the glass is a transmissive
dielectric with a very slight green tint, which is correct for period window glass.

Surfacing is restrained: the body carries a soft, uneven specular — spun brass rather than polished —
with darker patina collecting in the rolled seam, the vent louvres and the rivet recesses, plus light
bright wear on the bail pivot and the adjuster knob where hands would have held it. There is no heavy
damage, no dents and no soot on the glass, because the asset is meant to be reusable in a range of
lighting conditions.

This is a realistic interpretation with moderate stylisation in the wear pass; it is not a
photogrammetry scan, and it is not a replica of a specific museum object. Interior geometry of the
reservoir is not modelled — the reservoir is a closed shell.

---

## Dimensions and scale

| Dimension | Value |
| --- | --- |
| Width (X) | 0.162 m |
| Depth (Y) | 0.162 m |
| Height (Z) | 0.312 m |
| Ground footprint | 0.162 × 0.162 m |

Real-world metric scale. Origin at the centre of the base; the model sits on Z = 0 (Blender) /
Y = 0 (glTF). Up-axis +Y on export.

---

## Technical sheet

| Property | Value |
| --- | --- |
| Category | `hard-surface-prop` |
| Triangles | 48,210 |
| Vertices | 24,980 |
| Objects | 7 (parented under `lantern_root` empty) |
| Materials | 6 |
| Textures | 5 maps at 2048² (base colour, roughness, metallic, normal, AO) |
| UV layout | single UV set, non-overlapping, 8 px gutter, ~1450 px/m texel density |
| Formats | `.glb`, `.blend` |
| File sizes | `.glb` 18.4 MB, `.blend` 24.1 MB |
| Renders | 7 images, 2000 × 2000 px |
| Toolchain | Blender 4.2, Cycles, 160 samples, AgX view transform |
| LODs | none |
| Rig / animation | none — bail handle is a separate object and can be rotated by hand |

---

## Materials

| Material | Type | Base colour | Roughness | Metalness | Used on |
| --- | --- | --- | --- | --- | --- |
| `metal_brass_patinated` | PBR MR | `#C9A25E` | 0.34 | 1.00 | base, collar, vent cap, bail |
| `metal_steel_brushed` | PBR MR | `#8E9091` | 0.28 | 1.00 | wick spindle, rivets |
| `paint_enamel_red_worn` | PBR MR | `#7A2B24` | 0.52 | 0.00 | filler cap top face |
| `glass_soda_clear` | PBR MR + transmission | `#DCE6DE` | 0.04 | 0.00 | globe |
| `cork_seal` | PBR MR | `#8A6A46` | 0.88 | 0.00 | globe gasket |
| `leather_gasket` | PBR MR | `#4A3A2E` | 0.78 | 0.00 | filler cap gasket |

Materials are authored procedurally in Blender's node graph (wear and patina driven by curvature and
AO masks) and baked to the 2048² map set described above.

---

## Render set

| # | View | File |
| --- | --- | --- |
| 1 | Hero three-quarter | `renders/01-hero-three-quarter.png` |
| 2 | Front | `renders/02-front.png` |
| 3 | Side | `renders/03-side.png` |
| 4 | Back | `renders/04-back.png` |
| 5 | Top | `renders/05-top.png` |
| 6 | Detail — bail pivot and vent louvres | `renders/06-detail-bail-pivot.png` |
| 7 | Wireframe | `renders/07-wireframe.png` |

![Front view](renders/02-front.png)
![Side view](renders/03-side.png)
![Back view](renders/04-back.png)
![Top view](renders/05-top.png)
![Detail — bail pivot and vent louvres](renders/06-detail-bail-pivot.png)

All renders: 2000 × 2000 px, Cycles 160 samples with denoising, AgX view transform, three-point
studio lighting over a dark neutral backdrop with a subtle contact shadow. The glass globe is
rendered with a faint interior glow in the hero shot and unlit everywhere else, so the geometry stays
readable.

---

## Usage notes

- **Blender:** `File > Import > glTF 2.0` for the `.glb`, or open `model/brass-portable-lantern.blend`
  for the shader graphs and the (excluded) render rig.
- **Engines:** game-ready; metre scale, +Y up, scale factor 1.0. Parent empty `lantern_root` sits at
  the ground centre — rotate the empty to place the asset.
- **Transparency:** `glass_soda_clear` uses transmission in Cycles and alpha-blend in real-time
  engines. Put it in the transparent render queue and disable shadow casting if the shadow looks
  wrong; the glass is a thin single shell.
- **Print suitability:** not checked for printing. The guard wires are 1.2 mm at scale and will not
  survive most FDM prints at 1:1.

---

## Limitations & known issues

- Reservoir interior is not modelled — it is a closed shell, so you cannot simulate fuel or see inside
  through the filler neck.
- Glass is a single-sided shell; backface rendering must be enabled in real-time engines or the globe
  will appear to vanish from inside angles.
- The stamping on the base plate is generic and invented; there is no legible maker's mark.
- No LODs and no collision mesh are included. At 48k triangles the asset is intended for hero or
  mid-ground use, not for hundreds of instanced copies.
- Wear and patina are baked, not procedural in-engine, so re-tinting the brass requires editing the
  base-colour map rather than a shader parameter.
- Render set uses an emissive assist for the hero shot; the unlit glass will look slightly duller
  under engine lighting.

---

## Self-review

- [x] Real-world metric scale, origin at ground centre, transforms applied
- [x] Manifold, no ngons on curved surfaces, consistent normals, no z-fighting
- [x] Bevels on hard edges; deliberate, uniform density
- [x] All materials PBR with plausible values; no pure white/black
- [x] ≥ 5 renders ≥ 1600×1600; full model in frame with margin; no clipping
- [x] Three-point lighting; contact shadow present; no blown highlights or noise
- [x] Every render opened and inspected; contact sheet inspected
- [x] `renders.zip` mirrors `renders/`, opens cleanly, under 80 MB
- [x] `.glb` re-imported and verified against the renders
- [x] README complete; no placeholders; limitations are honest
- [x] `python tools/preflight.py agent_atlas` exits 0

---

## Licence & credits

- Geometry authored from scratch for this repository; no third-party mesh data used.
- Modelled in Blender 4.2 from reference photographs of late-19th-century railway hand lanterns
  (described and linked in `agent_atlas/NOTES.md`; no images redistributed).
- External assets: none. Studio lighting is procedural; no HDRI used.
- Licence: **CC BY 4.0** (see repository [LICENSE](../../LICENSE)).
