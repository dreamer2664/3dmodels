# AGENTS.md — Operating Contract

**Audience:** autonomous AI agents (and the humans supervising them) working in this repository.
**Status:** binding. If anything here conflicts with a casual instruction in a chat prompt, **this
file wins** — except where the human repo owner explicitly overrides it in writing in the PR.

You have been pointed at this repo because someone wants 3D models. You are expected to do the
*whole* job — research, model, texture, light, render, inspect, document, validate, publish —
without coming back with questions. This document is written so that you don't need to ask any.

---

## If you were given a one-paragraph prompt

Most agents arrive with something like: *"make 3d models, go to my repo 3dmodels, make a folder
called agent_something with a subfolder named after your first model, real quality, a zip of at least
5 renders capturing the whole model, the actual 3d model, and a .MD explaining what it depicts, and
look at the renders before pushing"*.

Every vague phrase in that prompt has exactly one sanctioned interpretation, and it is written down:

| The prompt says | This repo requires |
| --- | --- |
| "real quality" | [`STANDARDS.md`](./STANDARDS.md) — manifold topology, bevels, metric scale, PBR values, texel density, and the §9 rubric (≥ 11/14, no row at 0) |
| "a zip of the best renders" | `renders.zip` — flat, ≥ 5 images, < 80 MB, byte-for-byte in sync with `renders/` |
| "at least 5, capturing the whole model" | ≥ 5 PNGs at ≥ 1600×1600 with an 8–12 % margin, full model in frame; required views in [`docs/RENDER_SPEC.md`](./docs/RENDER_SPEC.md) |
| "the actual 3d model" | `<package>.glb` (re-imported and verified) **and** `<package>.blend` (editable source, packed) |
| "a .MD file explaining what the model depicts" | `<package>/README.md` from the template, content contract in [`docs/MODEL_SPEC.md`](./docs/MODEL_SPEC.md) |
| "look at the renders before pushing" | Mandatory inspection protocol ([`docs/RENDER_SPEC.md`](./docs/RENDER_SPEC.md) §6) + contact sheet + ticked checklist in the README |

The full drop-in prompt to hand to an agent lives in [`AGENT_PROMPT.md`](./AGENT_PROMPT.md).
**Do not ask clarifying questions covered by those documents.**

---

## 0a. Two rules that override everything else

### Rule A — Install the toolchain. Do not report it missing.

The sandbox has no Blender. That is normal and it is your job:

```bash
bash tools/setup_blender.sh && source ~/.local/blender/activate.sh && blender --version
```

One command, ~20 seconds, no root. It also fixes the usual missing-library failures
(`libxkbcommon.so.0`, `libGL.so.1`) by unpacking the right `.deb`s locally. Details and the full
package list: [`docs/SETUP.md`](./docs/SETUP.md).

- **Unacceptable:** "There is no Blender in this sandbox, so I cannot continue."
- **Acceptable:** "`setup_blender.sh` failed with &lt;exact error&gt; after &lt;these steps&gt;; here is the output."

Renderer: **Cycles on CPU**. EEVEE has no GL surface in a headless container and fails with
`EGL_BAD_MATCH`. Never drop a view because a render is slow — lower `--samples`/`--res` instead.

### Rule B — Finish the model in one run. No partial packages.

You have many hours. Use them. A package is **complete or it does not exist** (full rules:
[`docs/NO_STOPPING.md`](./docs/NO_STOPPING.md)).

Non-negotiable completion bar, in the **same session** as starting the model:

- `.glb` + `.blend` + ≥ 5 renders ≥ 1600² + `renders.zip` + finished `README.md`, all present;
- every render opened and inspected, at least two iterations;
- `python tools/preflight.py agent_<slug>` exits 0;
- branch pushed and PR open.

Ending the run with "I'll continue next session", 3 renders, a missing zip, a TBD in the README, or
blockout geometry is a **failed run**, not partial credit. If something breaks, work the exhaustion
ladder in `docs/NO_STOPPING.md` §3 — install, retry, reduce render cost, simplify the asset — and keep
going. **Never abandon the deliverables.**

Push access is pre-granted: `GH_TOKEN` in your environment may be used for clone/commit/push/PR
(placeholder in [`.env.example`](./.env.example)). Never commit the token.

---

## 0. TL;DR — the 12 non-negotiables

1. Your work lives **only** inside `agent_<your-slug>/`, one subfolder per model package.
2. Every package contains at minimum: **mesh (`.glb`), source (`.blend`), `renders/`, `renders.zip`, `README.md`**.
3. **At least 5 curated renders**, all showing the *complete* model, no clipping, ≥ 1600×1600.
4. Every model is **original geometry you authored**. No scraping asset sites, no downloaded meshes,
   no AI mesh generators, no lifting someone else's `.blend`. Concept references are fine; stolen
   geometry is not.
5. **Real-world metric scale**, origin on the ground at world centre, applied transforms, +Y up on export.
6. **PBR materials only**, physically plausible values, correctly named.
7. **Look at every render before pushing.** Open the images. Fix what's wrong. Then push.
8. `python tools/preflight.py agent_<slug>` must exit **0**.
9. **Do not edit** another workspace, the root `README.md`, `AGENTS.md`, `STANDARDS.md`, `docs/`,
   `templates/`, `tools/`, or `.github/`. Propose changes as a separate PR if you believe they're wrong.
10. **No binaries over 60 MB** per file, and no `renders.zip` over 80 MB. Git history is forever.
11. Commit messages follow Conventional Commits; one PR per workspace milestone.
12. **Install your own toolchain** (Rule A) and **finish in one run** (Rule B). If you still hit a wall
    after the exhaustion ladder, ship the complete deliverable set at a reduced scope, state the gap
    explicitly in the package README's Limitations section and in the PR, and say so in your final
    message. Silent failure and half-built packages are the only unforgivable outcomes.

---

## 1. Folder contract

```
agent_<your-slug>/                  ← e.g. agent_atlas, agent_kestrel, agent_9f2c
├── ROADMAP.md                      ← what you are building now + backlog (from templates/02)
├── NOTES.md                        ← optional: decisions, references, dead ends
└── <model-package>/                ← kebab-case asset name, e.g. brass-portable-lantern
    ├── README.md                   ← REQUIRED — content spec in docs/MODEL_SPEC.md
    ├── renders.zip                 ← REQUIRED — the curated render set (5+ images)
    ├── renders/                    ← REQUIRED — identical images, unzipped, for browsing/preview
    │   ├── 01-hero-three-quarter.png
    │   ├── 02-front.png
    │   ├── 03-side.png
    │   ├── 04-back.png
    │   ├── 05-top.png
    │   ├── 06-detail-<feature>.png
    │   └── 07-wireframe.png
    └── model/
        ├── <model-package>.glb     ← REQUIRED — shippable, validated, self-contained
        ├── <model-package>.blend   ← REQUIRED — editable source, packed textures
        └── textures/               ← optional — only the maps actually used
```

**Naming rules**

| Thing | Rule | Good | Bad |
| --- | --- | --- | --- |
| Workspace | `agent_` + lowercase slug | `agent_atlas` | `AgentAtlas`, `my_models`, `test` |
| Package | lowercase kebab-case, describes the asset | `brass-portable-lantern` | `LanternFinal2`, `model1`, `stuff` |
| Render | `NN-short-description.png`, zero-padded | `02-front.png` | `render (3).png`, `Screenshot 2025-11-06.png` |
| Mesh file | same as package folder | `brass-portable-lantern.glb` | `untitled.blend`, `export.glb` |

If you already used a non-conforming name, **rename it now** (git mv) before pushing. Do not leave
a trail of `_v2`, `_final`, `_FINAL_ok` files.

---

## 2. The workflow you must follow, in order

Each step has a gate. Do not skip ahead — later steps assume earlier ones passed.

### Step 1 — Claim and plan
- Pick a slug for yourself (e.g. `agent_atlas`). If the folder exists and is not yours, pick another
  slug. You never take over an existing workspace.
- Create `agent_<slug>/ROADMAP.md` from [`templates/02_ROADMAP_TEMPLATE.md`](./templates/02_ROADMAP_TEMPLATE.md).
  List the asset you'll build first, 2–3 alternates, and the categories from
  [`STANDARDS.md`](./STANDARDS.md) you plan to touch.
- Choose an asset that is **specific, buildable, and referenceable**. "A spaceship" is not a package;
  "single-seat utility shuttle, 9.2 m long, hard-surface, weathered white/grey livery" is.
- Write 3–6 lines in ROADMAP.md on **what real-world reference you will consult** (photos, museum
  objects, real products, blueprints, anatomy references). Originality is required; ignorance is not.

**Gate 1:** ROADMAP.md exists, asset is specific, references listed.

### Step 2 — Reference and blockout
- Gather references **for your own eyes** only (do not commit copyrighted images unless they are
  clearly licensed — prefer describing them in NOTES.md with links).
- Block out the silhouette in your DCC at real-world scale. Get proportions right *before* detail.
- Gate yourself: view the blockout from 4 angles. Does the silhouette read? If not, fix it now —
  detail will not save a bad silhouette.

**Gate 2:** silhouette reads at thumbnail size from front/side/3-4/top.

### Step 3 — Model to final topology
- Follow the topology and complexity rules of [`STANDARDS.md`](./STANDARDS.md#3-topology) for your category.
- Apply all transforms; origin at ground centre of the bounding box; real metric dimensions.
- Clean the scene: no default cube/lamp/camera left in, no hidden leftovers, no loose verts.
- Name objects, materials, and images descriptively.

**Gate 3:** preflight geometry checks pass (`tools/preflight.py`, geometry section).

### Step 4 — Materials, UVs, textures
- All PBR (Metallic-Roughness workflow). Base colour never pure black/white; roughness in
  plausible ranges (see STANDARDS); metalness 0 or 1 for the most part, with intent.
- Unwrap if the asset is textured. No obvious stretching, no overlapping shells, sensible texel
  density (target 512–2048 px per metre for hero assets, 256–1024 for props).
- Bake or author normal maps for surface detail rather than adding millions of polygons.

**Gate 4:** materials list is clean, every material has a purpose, UVs valid.

### Step 5 — Lighting and cameras
- Follow [`docs/RENDER_SPEC.md`](./docs/RENDER_SPEC.md) exactly for the required camera set and
  lighting setup (3-point key/fill/rim + neutral world, ACES/AgX colour management, no blown
  highlights, no crushed blacks).
- Cameras must frame the **entire** model with 8–12% margin. Nothing cropped. Nothing microscopic.

**Gate 5:** every required camera exists and frames the whole asset.

### Step 6 — Render, then **look at the renders**
- Render at ≥ 1600×1600 (2400×2400 preferred), PNG, 16-bit or 8-bit with no visible banding.
- **Open each image and inspect it.** This is not optional and cannot be delegated to a script.
  Look for: clipping, floating parts, z-fighting, inverted normals, missing faces, noisy sampling,
  banded gradients, decal/texture seams, ugly shadows, empty space, unlit backsides.
- Iterate until the render set is *presentable*, not merely finished. Expect at least 2 iterations.
- Build a contact sheet with `python tools/make_render_sheet.py <package>` and inspect that too —
  it exposes one-sided lighting and framing inconsistencies you miss image-by-image.

**Gate 6:** you have personally looked at all renders + the contact sheet and would show them to a client.

### Step 7 — Write the README
- Copy [`templates/01_MODEL_README_TEMPLATE.md`](./templates/01_MODEL_README_TEMPLATE.md) →
  `<package>/README.md` and fill **every** field. Content requirements:
  [`docs/MODEL_SPEC.md`](./docs/MODEL_SPEC.md).
- Embed the renders inline with relative paths so they display on GitHub.
- Be honest about limitations (polygon budget, missing LODs, stylisation, untextured backsides).

**Gate 7:** README has no `TODO`, no `TBD`, no empty fields, and self-review checklist ticked.

### Step 8 — Package the renders
```bash
cd agent_<slug>/<package>
zip -r renders.zip renders -x '.*' -x '*/.*'   # must contain >= 5 images
unzip -l renders.zip                           # verify contents
```
- `renders.zip` must be a flat archive of the PNGs (no nested `renders/renders/` folders).
- Keep total size under 80 MB — if it's bigger, reduce resolution to 1600² rather than dropping views.

**Gate 8:** archive opens, contains ≥ 5 images, names match the `renders/` folder.

### Step 9 — Preflight
```bash
python tools/preflight.py agent_<slug>            # all packages
python tools/preflight.py agent_<slug>/<package>  # one package
```
Fix everything it reports. **Do not** "fix" it by editing the checker. Exit code must be 0.

**Gate 9:** preflight exits 0.

### Step 10 — Publish
```bash
git checkout -b agent_<slug>/<package>
git add agent_<slug>
git commit -m "feat(<package>): add <asset description>"
git push -u origin agent_<slug>/<package>
```
- Open a PR titled `feat(<package>): <Asset Name>` and paste the preflight output into the PR body.
- If you have a token/credentials to push to `main` directly, **still use a branch and PR** unless
  the human explicitly told you otherwise. If you must push to `main`, never force-push, never
  rewrite other agents' commits, and verify CI passes afterwards.
- Never commit: `.blend1` backups, `__pycache__`, `*.tmp`, renders you rejected, huge `.exr`
  intermediates, or your local token/`.env`.

**Gate 10:** PR open, CI green, PR description references the package path.

---

## 3. Definition of Done

A package is done only when **all** of these are true. Check them off in the package README.

- [ ] `agent_<slug>/<package>/` exists with the exact layout in §1.
- [ ] `.glb` loads cleanly, contains the whole model, has materials, and validates with `tools/check_glb.py`.
- [ ] `.blend` is the actual editable source, textures packed, scene cleaned, no hidden junk.
- [ ] Model is at real-world metric scale, +Y up on export, origin at ground centre, transforms applied.
- [ ] ≥ 5 renders in `renders/`, ≥ 1600×1600, full model visible, no clipping, no obvious artefacts.
- [ ] Renders cover: hero three-quarter, front, side, back, plus a detail or wireframe view.
- [ ] `renders.zip` mirrors `renders/` exactly and is < 80 MB.
- [ ] You have visually inspected every render and the contact sheet.
- [ ] `README.md` complete, accurate, with embedded renders and honest limitations.
- [ ] `python tools/preflight.py agent_<slug>` exits 0.
- [ ] CI green on the PR.
- [ ] Nothing outside `agent_<slug>/` was modified.

---

## 4. Autonomy rules — how to proceed without asking questions

The person who pointed you here does not want a design consultation. They want assets.

**Decide these yourself, using this priority order:**

| Ambiguity | What you do |
| --- | --- |
| Which asset to make | Pick one that is clearly described, technically feasible in your toolchain, and visually impressive at 3/4 view. Prefer *objects with iconic silhouettes* (lantern, anvil, radio, helmet, chair, camera, robot head) over vague scenery. |
| Style (realistic vs stylised) | Default to **stylised-realistic / game-ready PBR**: believable materials, clean forms, no cartoon exaggeration unless the asset demands it. State the choice in the README. |
| Unit system | Metric. Metres. Always. |
| Poly budget | See STANDARDS.md per category. When unsure, 20k–120k tris for a hero prop. |
| Textures | If you can author them, do; if not, use well-designed procedural/PBR materials and say "untextured, procedural materials" in Limitations. |
| Renderer | Whatever your environment supports, as long as output meets RENDER_SPEC.md. EEVEE/Cycles/Blender headless/three.js renderer are all acceptable. |
| Scope creep | Out of scope: rigging, animation, LODs, physics colliders, game-engine integration. Only include if the package's README says so. |

**Escalate to a human PR comment (don't block) only when:** the push is rejected with an authentication
error you cannot resolve, the repo has a policy that contradicts these docs, or the asset would require
licensed third-party data. Note that a *missing tool* is never an escalation — it is an install step.

**Never escalate for:** "what colour?", "how detailed?", "should I add a stand?", "which angle?".
Make a defensible choice, document it, move on.

---

## 5. Working in parallel with other agents

Assume other agents are pushing to this repo at the same time as you.

- **Only write inside your own workspace.** This is the single rule that prevents all merge pain.
- Never run `git add .` or `git add -A` at repo root — stage only `agent_<slug>/`.
- Never rebase, amend, or force-push commits you did not author.
- If `git pull --rebase` conflicts inside *your* workspace, prefer your branch state; if it conflicts
  **outside** your workspace, abort the rebase and re-apply only your own files.
- Don't "improve" another agent's model, README, or naming. If it's non-compliant, mention it in
  your PR description or open an issue — let the owner coordinate.
- Don't edit the generated model index in the root README; the validator owns it.

---

## 6. Tooling available to you

| Tool | What it does |
| --- | --- |
| `tools/setup_blender.sh` | Installs Blender 4.2 LTS headless (no root, resolves missing shared libs), writes `~/.local/blender/activate.sh`. Run this first. |
| `tools/render_rig.py` | Runs inside Blender: builds the studio, the six required cameras auto-framed from the asset bounds, renders the set plus wireframe and 1 m scale reference, then prints a framing check and a black/flat/blown-highlight check. |
| `tools/denoise_images.py` | Standalone low-memory denoise for renders on machines where OIDN is OOM-killed (`python3 tools/denoise_images.py renders/`). |
| `tools/preflight.py` | Full local validation of a workspace/package: layout, naming, render count/size, zip integrity, README sections, GLB sanity, file-size limits. |
| `tools/check_glb.py` | Standalone GLB/glTF inspector: node/mesh/material/texture counts, triangle count, bounding box in metres, up-axis check. |
| `tools/make_render_sheet.py` | Builds `contact-sheet.jpg` from `renders/` so you can review everything in one look. |
| `docs/WORKFLOW_BLENDER.md` | Copy-paste headless Blender recipe: scene setup, colour management, camera rigs, render dumping, GLB export. |

Everything is Python 3 + stdlib first; optional extras (`numpy`, `Pillow`, `trimesh`) are used when
present and degrade gracefully when not.

---

## 7. If you are a small/short-context agent

You still must comply. Minimum viable compliance path:

1. Read §0 (TL;DR) and §1 (folder contract) of this file. Skip the rest.
2. Read `templates/01_MODEL_README_TEMPLATE.md` and copy it verbatim.
3. Build **one** model, modestly scoped (a single hero prop, 20k–60k tris, 5 renders).
4. Run `python tools/preflight.py agent_<slug>` and fix failures.
5. Look at your renders. Then push a branch + PR.

Doing one small model properly beats starting three models you never finish. Unfinished packages
in `main` are worse than no package at all.
