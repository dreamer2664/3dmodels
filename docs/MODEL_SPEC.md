# MODEL_SPEC.md — Required content of a package `README.md`

Every model package has a `README.md` at its root. It must answer, completely and honestly, what the
object is, how it was built, and how to use it. This document defines the required content; the
skeleton lives in [`templates/01_MODEL_README_TEMPLATE.md`](../templates/01_MODEL_README_TEMPLATE.md).

The write-up is graded. A perfect model with a thin README fails review; a good model with an
excellent README passes.

---

## 1. Front-matter block (machine-readable)

Start the file with a fenced `yaml` block so the tooling can index packages:

```yaml
---
model: brass-portable-lantern
package: brass-portable-lantern
workspace: agent_atlas
category: hard-surface-prop
version: 1.0.0
status: released            # draft | in-review | released | deprecated
author_agent: agent_atlas
created: 2026-11-06
license: CC-BY-4.0
dimensions_m: {x: 0.16, y: 0.16, z: 0.31}   # width, depth, height — metres
triangles: 48210
vertices: 24980
objects: 7
materials: 6
textures: 5
formats: [glb, blend]
render_count: 7
render_min_resolution: 1600
software: [Blender 4.2, Cycles]
brief: "brass portable lantern"   # the WANTED.md line this fulfils, or "prompt"
brief_source: owner            # owner | pack | agent | prompt
---
```

Rules: metric dimensions, accurate triangle count (post-triangulation), real `software` list,
`status: released` only after preflight passes, and `brief` / `brief_source` filled in so the owner can
trace every package back to a line in [`WANTED.md`](../WANTED.md).

---

## 2. Required sections

### 2.1 Title + one-line summary
`# Brass Portable Lantern` then a single sentence: what it is, in plain language.

### 2.2 Hero render
The `01-hero-three-quarter.png` embedded immediately. First impression matters.

### 2.3 What this model depicts  *(the section the human actually asked for)*
3–6 paragraphs of literal description. Cover:
- **Identity:** what the object is, its function, and the period/context if relevant.
- **Form:** overall shape, proportions, defining features, how it is assembled.
- **Parts:** enumerate the notable sub-parts (base, fuel reservoir, glass globe, burner, bail handle,
  collar, vent cap...) and what each does.
- **Materials:** what each part is made of in the real world, and what material you used.
- **Surface & wear:** finish, wear, patina, dirt, signage.
- **What it is *not*:** if it is a stylised or semi-fictional interpretation, say so here.

No marketing language. Measurements over adjectives. "31 cm tall, 16 cm at the base" beats "tall and
elegant".

### 2.4 Dimensions and scale
A small table of true dimensions in metres plus a sentence confirming real-world scale and origin
placement ("origin at the centre of the base, model sitting on Z = 0").

### 2.5 Technical sheet
Table: category, triangles, vertices, objects, materials, texture set + resolutions, UV layout notes,
format list, file sizes, generator/toolchain, LODs (if any), animation/rig (if any).

### 2.6 Materials list
One row per material: name, type (PBR metallic-roughness), base colour hex, roughness, metalness,
and what part(s) it is used on. Optionally a one-line note on how it was authored (procedural, baked,
hand-painted).

### 2.7 Render set
Embed **every** render with a caption that says what the view is and why it exists. This section is
the gallery; it doubles as proof that all sides are finished.

### 2.8 Usage notes
- How to import (Blender, three.js, Unity/Unreal, glTF viewers).
- Orientation, units, pivot behaviour, scale factor if the target engine differs.
- Whether it is game-ready, viz-ready, or print-oriented.
- Anything a technical artist needs to know before dropping it in (e.g. "no LODs", "single material
  atlas", "transparent glass uses alpha blend — set render queue appropriately").

### 2.9 Limitations & known issues  *(mandatory, must be honest)*
Bullet list. Examples of acceptable entries:
- "Backfaces of the interior are simplified — not intended for extreme close-ups."
- "Procedural materials only; no baked texture set, so it will not match exactly in engines with
  limited shader support."
- "No LODs or collision mesh."
- "Glass is a single-sided surface; enable double-sided rendering or use the provided config."
Empty or wishy-washy limitation sections ("none, it's perfect") are rejected. There are always
limitations.

### 2.10 Self-review checklist
Tick every box from [`REVIEW_CHECKLIST.md`](./REVIEW_CHECKLIST.md) inline in the README.

### 2.11 Licence & credits
`CC BY 4.0` unless declared otherwise. Credit every external source used (CC0 HDRIs, fonts, etc.).
State explicitly: "geometry authored from scratch; no third-party mesh data used."

---

## 3. Writing style

- English, plain, concrete, third person or neutral imperative.
- No filler, no hype, no emoji, no "Lorem".
- Tables for anything enumerable.
- Relative image paths (`renders/01-hero-three-quarter.png`) so GitHub renders them inline.
- Headings in sentence case or title case consistently.
- If you include numbers, make them real. Wrong triangle counts and invented dimensions are worse
  than omitting them — run `tools/check_glb.py` and copy its output.

---

## 4. Quality gate for the README

A README passes when:

- [ ] Front-matter block parses and every field is filled with real data.
- [ ] All required sections §2.1–§2.11 present, in order.
- [ ] "What this model depicts" is at least 3 substantive paragraphs and mentions every major part.
- [ ] Every render is embedded and captioned.
- [ ] Materials table matches the actual materials in the `.glb`.
- [ ] Dimensions match the actual bounding box.
- [ ] Limitations section is non-empty and honest.
- [ ] No `TODO`, `TBD`, `XXX`, `FIXME`, placeholders, or template boilerplate left behind.
- [ ] Checklist ticked.
