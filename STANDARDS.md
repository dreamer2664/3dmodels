# STANDARDS.md — Asset Quality Standards

These are the acceptance criteria for every 3D asset in this repository. They are intentionally
demanding: the point of this repo is a shelf of assets that look like they came from a professional
studio, not a pile of first drafts.

Where a rule says **MUST**, a reviewer may reject on it. Where it says **SHOULD**, you need a
stated reason in the package README if you deviate.

Numbers are defaults per category. Category is declared in the package README front-matter.

---

## 1. Categories and their budgets

| Category | Description | Tri budget (typical) | Render set emphasis |
| --- | --- | --- | --- |
| `hard-surface-prop` | Manufactured objects: tools, devices, machines, furniture, weapons | 15k – 150k | full orthographic set + 1 macro detail |
| `architecture` | Buildings, interiors, modular kits, environmental structures | 30k – 400k | eye-level + aerial + interior/detail |
| `organic` | Creatures, characters, plants, food | 30k – 300k | front/side/back + face or feature close-up |
| `vehicle` | Cars, aircraft, watercraft, sci-fi craft | 50k – 500k | 3/4 + front + side + top + detail |
| `environment` | Scenes, terrain, dioramas | 100k – 1M (or instanced) | ≥ 2 wide shots + 2 detail shots |
| `stylised` | Deliberately simplified/low-poly art direction | 500 – 20k | full set + wireframe (topology is the product) |
| `product-viz` | Marketing-quality single object, highest fidelity | 80k – 600k | studio hero + 3 orthos + 2 macro details |

**Budgets are caps for the "hero" representation, not targets.** A 9,000-triangle lantern that is
perfectly modelled beats a 90,000-triangle lantern with lumpy surfaces. Excess density must be
justified — you may not hit a budget by subdividing.

---

## 2. Geometry and topology

### MUST
- **Manifold** for solid objects: no holes, no non-manifold edges, no interior faces (except where
  legally required for e.g. open shells, which must be declared).
- **No ngons** on curved or deforming surfaces. Quads preferred; triangles acceptable on flat planes
  and at the end of tapered forms. Ngons on a flat capped face are tolerable, ngons on a bevel are not.
- **No degenerate geometry**: zero-area faces, zero-length edges, duplicate vertices within 0.1 mm,
  non-normalised normals, flipped faces.
- **Uniform, deliberate density.** Even spacing on curved surfaces; extra loops where the form
  changes (creases, bevels, intersections). No "pinching" at poles or bevel corners.
- **Bevels on every hard edge** that catches light. Physical objects do not have infinitely sharp
  edges: use 1–3 loops (or a bevel modifier applied) with a radius between 0.5 mm and 3 mm for
  hand-scale objects, scaled proportionally for larger assets. Exceptions: cutting blades, paper,
  and stylised low-poly (declare it).
- **Support loops** around booleans and intersections so subdivision or normal shading behaves.
- **Applied transforms**: rotation/scale at 1.0, location may be non-zero only if you also declare
  origin placement. **Scale MUST be (1,1,1).**
- **Real-world scale in metres.** A coffee mug is 0.09 m tall. A door is 2.05 m. Verify against a
  human-scale reference in at least one render (see RENDER_SPEC).
- **Origin:** object origin at the centre of the model's ground contact, model sitting on Z=0 (Blender)
  / Y=0 (glTF). Nothing floating at 1.7 m by accident.
- **Separate objects** where the real thing separates (a lid is a separate object from the body) and
  name them accordingly; join what is one physical piece. Do not ship 400 loose objects — group into
  ≤ 20 logical parts and parent them under an empty named after the asset.

### SHOULD
- Face orientation consistent (all outward) and normals averaged consistently.
- Axis-aligned where the design is axis-aligned — do not leave parts rotated by 0.3°.
- Symmetry used deliberately for organic forms, broken deliberately for realism (asymmetry where the
  real object is asymmetric — a worn tool, a leaning chair).
- No "kitbash sludge": imports of unrelated greeble packs. If you use a greeble kit you authored
  yourself inside your own workspace, that's fine.

### Forbidden
- Default cube / default monkey / default lamp in the final file.
- Unapplied Subdivision Surface or Bevel modifiers in the exported `.glb` (apply or export with
  apply so what you see is what ships).
- z-fighting coplanar decals — offset by ≥ 0.2 mm or use a proper decal/material solution.
- Hidden geometry padding the bounding box.
- Sub-pixel-thin geometry that renders as a line from 3 m away unless that is the intent.

---

## 3. UVs and texturing

### If the asset uses textures (recommended for hero assets)
- **MUST** unwrap with no overlapping UV shells (except for intentional, declared tiling and
  symmetrical mirrored UVs — mirrored UVs must be declared).
- **MUST** keep texel density consistent within ±20% across the asset.
  Target: 512–2048 px/m for hero assets, 256–1024 px/m for background props.
- **MUST** leave a 4–8 px padding/gutter between shells to avoid seam bleeding at mip levels.
- Maps must be power-of-two (512, 1024, 2048, 4096) except for atlases with a stated reason.
- Use the **Metallic-Roughness** PBR workflow with these maps where applicable:
  Base Color (sRGB), Roughness (linear), Metallic (linear), Normal (linear, OpenGL +Y for glTF),
  Ambient Occlusion (linear, optional but preferred), Emissive (sRGB, only if the object emits).
- Pack textures into the `.blend`; list every map in the README with its resolution.
- **No visible seams, stretching, or mirrored text/logos.** Nothing says "amateur" faster than
  backwards lettering.

### If no textures (procedural materials only)
- **MUST** be stated in the README's Limitations as "procedural materials, no baked texture set".
- Materials must still vary: no single flat colour across a whole object unless it is a deliberate
  stylised choice. Use subtle roughness variation, edge wear, or a grunge mask.

---

## 4. Materials

### MUST
- **Physically plausible values.** Guidance:
  - Metals: metallic 1.0, base colour = the metal's reflectance (steel ≈ 0.56 grey, aluminium ≈ 0.91,
    gold ≈ (1.00, 0.77, 0.34), copper ≈ (0.96, 0.64, 0.54)). Never metallic 1.0 with base colour black.
  - Dielectrics: metallic 0.0, roughness 0.25–0.9 depending on finish.
  - Roughness: no uniform 0.5 across all materials. Glass/water < 0.1, polished metal 0.1–0.2,
    brushed metal 0.25–0.4, painted surface 0.4–0.6, rubber/fabric 0.7–0.95.
  - Base colour: **never pure white (#FFFFFF) or pure black (#000000)**. Use 0.02–0.9 sRGB range.
    Pure white/black is physically impossible and destroys render quality.
- **No default materials.** No "Material.001" carrying over with roughness 0.5.
- **Named by purpose**: `paint_enamel_cream`, `metal_brass_brushed`, `glass_clear_smoked`, `rubber_black`.
- **Consistent naming across the asset**, prefixed by type.
- Emissive materials: emissive strength stated in the README; must not blow out the render into a
  white blob. If the object glows, the render must show its surrounding falloff.
- Transparency: use it only with a stated reason, correct blend mode, and no sorting artefacts in
  renders. Prefer refraction-free alpha for thin surfaces.

### SHOULD
- Subtle imperfections: edge wear, occlusion darkening, dust in crevices, fingerprints on glass.
  Restraint is part of the craft — a hero asset shouldn't look like it fell in mud.
- Consistent art direction across the whole object: one metal palette, one accent colour family.

---

## 5. Renders

**Full technical spec in [`docs/RENDER_SPEC.md`](./docs/RENDER_SPEC.md).** Summary of the MUSTs:

- **≥ 5 images**, **≥ 1600×1600** px, PNG, sRGB, opaque background (dark neutral or light neutral —
  not transparent, not a checkerboard).
- The **complete model** must be visible in every "whole model" shot: **8–12 % empty margin** on all
  sides, nothing cropped, nothing clipped by the camera near plane.
- **Required views:** hero 3/4, front, side (left), back, top-or-bottom. Plus at least one of:
  macro detail of the most interesting feature, or a wireframe/topology shot.
- **Lighting:** 3-point minimum (key, fill, rim) or an HDRI-equivalent studio setup. No single
  flat frontal light. No blown highlights (no pixel clusters at 255 in the base colour pass).
  No crushed blacks (no pixel clusters at 0 in the large dark regions unless a deliberate silhouette).
- **Colour management:** ACES or AgX/Standard with a filmic look; no double-gamma.
- **Shadows:** contact shadow present and anchored — the object must look like it's sitting on
  something. Floating objects with no grounding shadow are rejected.
- **No artefacts:** noise/fireflies (raise samples), banding, z-fighting, missing faces, see-through
  backfaces, seam-torn textures, jagged aliasing (use ≥ 64 samples + denoise or supersample).
- **Consistency:** all renders of one package share exposure, world, and framing philosophy. A set
  that looks like 5 different scenes is a failed set.
- **Human scale reference:** at least one render SHOULD include a subtle scale cue (a grid floor with
  1 m lines, or a silhouette/measurement annotation). Declare scale in the README regardless.

---

## 6. Documentation

### MUST
- `<package>/README.md` filled from [`templates/01_MODEL_README_TEMPLATE.md`](./templates/01_MODEL_README_TEMPLATE.md),
  content requirements in [`docs/MODEL_SPEC.md`](./docs/MODEL_SPEC.md).
- Contains: what the object **is**, what it depicts in detail (form, materials, parts, function,
  history or real-world referent), dimensions, category, poly count, format list, how to use, and a
  **limitations** section.
- Renders embedded with relative markdown paths, so they render on GitHub without clicking through.
- No `TODO`, `TBD`, `Lorem ipsum`, or placeholder bullets.
- Written in English, plain and concrete. Prefer measurements over adjectives.
- Describes the model **as shipped**, not as intended. If you planned a texture set and shipped
  procedural, the README says procedural.

### SHOULD
- A short "design notes" paragraph explaining the modelling decisions (why these proportions, which
  reference drove the form).
- Palette table with hex values of the main materials.

---

## 7. File and repository hygiene

| Rule | Limit |
| --- | --- |
| Any single committed file | ≤ 60 MB |
| `renders.zip` | ≤ 80 MB, must open cleanly |
| Images per package in `renders/` | 5–12 (more is clutter; curate) |
| Objects per package (mesh) | ≤ 20 logical parts, parented |
| Materials per package | ≤ 25, all named and used |
| Textures per package | ≤ 12 maps, PO2 sizes |
| Package folder depth | fixed layout in AGENTS.md §1 |

Forbidden in commits: `.blend1`, `*.exr`/`*.hdr` intermediates, `__pycache__`, `.DS_Store`,
`Thumbs.db`, `node_modules`, render caches, `.env`, tokens, keys, local absolute paths in scripts,
and any file over the size limit. Add a `.gitignore` inside your workspace if your tooling produces
junk.

---

## 8. Originality, licensing, and ethics

- The **geometry must be authored by you** in this repo's effort. Referencing photographs or
  diagrams to inform form is encouraged. Downloading, scraping, or converting someone else's mesh
  is prohibited, including via "free" asset sites. AI-generated *meshes* are prohibited; AI-assisted
  *textures* must be declared in the README and must not infringe on identifiable IP.
- Do **not** reproduce identifiable copyrighted characters, logos, or trademarked designs. Use
  "in the style of" generic forms instead. A generic "utility lantern" is fine; a named movie prop
  is not.

### Sanctioned interpretation (do not stall on these)

- **A branded product request** (a phone, a car, a watch, a sneaker) is satisfied by a **generic,
  unbranded object of that type**: correct form factor and proportions, no logos, no distinctive
  trademarked silhouette, no brand text. Slug it by type (`smartphone-slab`, not `iphone`) and state
  in the README: "a generic <type>; not a replica of any branded product."
- **A person request** is satisfied by an **invented character**, never a likeness: no real
  individual, no celebrity, no reference photograph of a real person committed to the repo.
  Direction like age, build, clothing or a skin-tone palette choice is fine — the result must be a
  character you invented. State in the README: "invented character; not a likeness of any person."
- **Never stop to ask.** Build the generic version, record the interpretation in the package README
  (`brief_interpretation:` in the front-matter), and continue.
- Do not include personally identifying information, real faces of real people (without consent),
  or military insignia of real nations if it could be seen as endorsement.
- Everything is released under the repo [LICENSE](./LICENSE) (CC BY 4.0) unless the package README
  declares an exception the owner approved.

---

## 9. Scoring rubric (used for review and for self-assessment)

Rate your own package before pushing. **Fail any row = do not push.**

| Dimension | Fail (0) | Pass (1) | Excellent (2) |
| --- | --- | --- | --- |
| Silhouette & proportion | unreadable / wrong proportions | reads correctly | instantly recognisable, well-balanced |
| Topology | ngon soup, non-manifold, pinching | clean, deliberate | production-grade, subdivision-friendly |
| Surface detail | featureless primitives | believable bevels & panels | craft-level detail where it matters |
| Materials | flat default colours | plausible PBR | art-directed, subtle imperfection |
| Renders | cropped, noisy, flat light, < 5 | spec-compliant set | portfolio-quality, consistent set |
| Documentation | incomplete / placeholder | all sections filled | genuinely informative, honest, useful |
| Hygiene | junk files, broken zip, default objects | clean | exemplary naming & structure |

Target: **≥ 11 / 14** with no row at 0. That is the bar.
