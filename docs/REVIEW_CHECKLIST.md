# REVIEW_CHECKLIST.md

Tick every box in your package `README.md` before pushing. A reviewer — human or agent — will re-run
this list. Unchecked boxes mean the package is not done; dishonest ticks mean it gets rejected.

---

## A. Structure

- [ ] Workspace folder is `agent_<slug>` (lowercase, underscore-separated).
- [ ] Package folder is `<kebab-case-asset-name>`.
- [ ] Contains `model/<package>.glb`, `model/<package>.blend`, `renders/`, `renders.zip`, `README.md`.
- [ ] Nothing outside my workspace was modified.
- [ ] No `.blend1`, `__pycache__`, `.DS_Store`, temp files, or rejected renders committed.
- [ ] No file exceeds 60 MB; `renders.zip` is under 80 MB and opens cleanly.

## B. Model

- [ ] Real-world metric scale, verified against a reference (grid floor, known dimension, human scale).
- [ ] Origin at ground-centre; model sits on the ground plane; transforms applied (scale = 1).
- [ ] Manifold where the object is solid; no interior faces, no loose geometry, no doubles.
- [ ] No ngons on curved surfaces; no pinching at bevel corners or poles.
- [ ] Bevels on hard edges that catch light; support loops where the form changes.
- [ ] Consistent outward normals; no z-fighting.
- [ ] Object/material/texture names are descriptive; ≤ 20 objects, ≤ 25 materials.
- [ ] Detail level appropriate to the category budget; density is deliberate, not subdivided mush.
- [ ] Silhouette reads instantly at thumbnail size from the 3/4 view.
- [ ] Re-imported the `.glb` and confirmed it matches the renders.

## C. Materials & UVs

- [ ] All materials are PBR metallic-roughness with plausible values.
- [ ] No pure white/black base colours; no uniform roughness across every material.
- [ ] Textured assets: UVs unwrapped, no overlapping shells (or declared), consistent texel density,
      gutter padding, no stretching or mirrored text.
- [ ] Every map listed in the README with resolution; textures packed into the `.blend`.
- [ ] Procedural-only assets declare that in Limitations.

## D. Renders

- [ ] ≥ 5 images, all ≥ 1600×1600, square, opaque neutral background, PNG.
- [ ] Required views present: hero 3/4, front, side, back, top, detail.
- [ ] Whole model in frame with 8–12 % margin — no clipping anywhere; **I zoomed the corners and checked**.
- [ ] Three-point lighting: key, fill, rim; no flat frontal-only light.
- [ ] Contact shadow present; object grounded.
- [ ] No blown highlights, crushed blacks, noise, fireflies, banding, or aliasing.
- [ ] Correct colour management; all shots share exposure and world.
- [ ] **I opened every render and inspected it.**
- [ ] **I built and inspected the contact sheet** (`tools/make_render_sheet.py`).
- [ ] Rejected iterations were discarded, not committed.

## E. Rendering archive

- [ ] `renders.zip` contains ≥ 5 images with the same filenames as `renders/`.
- [ ] Archive is flat (no nested `renders/` folder inside it).
- [ ] Archive size within limits and verified with `unzip -l`.

## F. Documentation

- [ ] `README.md` created from the template, all sections present and filled.
- [ ] Front-matter block filled with real values (triangles, dimensions, materials, render count).
- [ ] "What this model depicts" is substantive and covers every major part.
- [ ] Dimensions and triangle counts match the actual files.
- [ ] Materials table matches the actual materials in the `.glb`.
- [ ] All renders embedded with relative paths and captions.
- [ ] Limitations section is non-empty and honest.
- [ ] Usage notes tell a technical artist how to import and any gotchas.
- [ ] No `TODO`/`TBD`/placeholder text anywhere.
- [ ] Licence and credits stated; confirms no third-party mesh data.

## G. Validation & publication

- [ ] `python tools/preflight.py agent_<slug>` exits 0.
- [ ] `python tools/check_glb.py <package>/model/<package>.glb` reports a valid mesh.
- [ ] Branch named `agent_<slug>/<package>`; commit message follows Conventional Commits.
- [ ] Only my workspace is staged (`git add agent_<slug>`, never `git add -A` at root).
- [ ] PR opened with package path, category, tri count, render count, and preflight output.
- [ ] CI green.

---

### Reviewer notes (for the human/agent reviewing this PR)

| Score | Meaning |
| --- | --- |
| **Reject** | any unchecked box, any dishonest claim, or rubric row scoring 0 |
| **Request changes** | meets minimums but rubric total < 11/14, or renders are technically compliant but visually weak |
| **Approve** | all boxes ticked, rubric ≥ 11/14, nothing embarrassing in the render set |
