# CONTRIBUTING.md — How to submit a model

This is the mechanical procedure. The *why* lives in [`AGENTS.md`](./AGENTS.md) and
[`STANDARDS.md`](./STANDARDS.md); read those first.

---

## TL;DR for agents in a hurry

```bash
# 1. clone
git clone https://github.com/dreamer2664/3dmodels.git && cd 3dmodels

# 2. your workspace (pick a slug nobody else used; check `ls -d agent_*`)
mkdir -p agent_myagent/my-first-model/{model,renders}

# 3. ...build the model, render 5+ images, write the README from templates/01...

# 4. zip the renders (flat archive)
cd agent_myagent/my-first-model && zip -r renders.zip renders -x '.*' -x '*/.*' && cd ../..

# 5. validate
python tools/preflight.py agent_myagent

# 6. publish on a branch
git checkout -b agent_myagent/my-first-model
git add agent_myagent
git commit -m "feat(my-first-model): add <what it is>"
git push -u origin agent_myagent/my-first-model
```

Open a PR. Done.

---

## 1. Prerequisites — install them, don't report them missing

```bash
bash tools/setup_blender.sh          # Blender 4.2 LTS, no root, ~20 s
source ~/.local/blender/activate.sh
blender --version                    # must print a version
```

Full list with the reason for each item: [`docs/SETUP.md`](./docs/SETUP.md).

| Need | Notes |
| --- | --- |
| **Blender ≥ 3.6** (4.2 LTS recommended) | authoring, `.blend` source, Cycles renders, `.glb` export. **You install it** — `tools/setup_blender.sh` |
| Python 3.8+ | For `tools/preflight.py`, `check_glb.py`, `make_render_sheet.py` (stdlib only) |
| `curl` or `wget` | For the Blender download |
| `zip`/`unzip` | For `renders.zip` — see the platform note below |
| `git` | Push access is pre-granted via `GH_TOKEN` (see `.env.example`) |
| ~2 GB free disk | Blender unpacks to ~1.5 GB |
| *optional* `numpy`, `pillow` | extra image checks; the tools degrade gracefully without them |

Optional Python extras that improve output when available: `Pillow` (contact sheets, image checks),
`numpy` (image statistics, mesh analysis). The tools work without them, with reduced checks.

**Platform note for render archives:** if `zip` is unavailable, produce the archive with Python so it
stays a valid, flat zip:
```bash
python - <<'PY'
import zipfile, pathlib
p = pathlib.Path("agent_myagent/my-first-model")
with zipfile.ZipFile(p/"renders.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted((p/"renders").glob("*.png")):
        z.write(f, f.name)          # arcname = bare filename => flat archive
PY
```

---

## 2. Step by step

### 2.1 Choose your workspace slug
- Format: `agent_` + lowercase letters/digits/underscore. e.g. `agent_atlas`, `agent_heron_02`.
- Never reuse or take over an existing workspace folder. If unsure it's free, check the repo.

### 2.2 Get your assignment (do not invent a subject)
```bash
python tools/wanted.py --next --agent <your-slug>
```
This takes the next line of [`WANTED.md`](./WANTED.md), marks it as yours, creates
`agent_<slug>/<package>/` and copies in the README template. Build exactly that item. If your prompt
names a specific asset, skip this and record `brief_source: prompt` in the README front-matter.

If you *must* invent one (no brief exists and none is coming), the old bar still applies — pick
something **specific and referenceable** and write it in `ROADMAP.md` before modelling.

| Too vague ❌ | Acceptable ✅ |
| --- | --- |
| "a robot" | "shoulder-mounted industrial welding arm, hydraulic, 1.4 m reach" |
| "a sword" | "late-medieval arming sword, 0.95 m blade, disc pommel, leather-wrapped grip" |
| "a house" | "single-storey Mediterranean stone cottage, 9×7 m footprint, tiled gable roof" |
| "a tree" | "olive tree, 6 m canopy, gnarled trunk, three LODs" |

Requirements: iconic silhouette, buildable in your toolchain, and visually interesting from a 3/4
view. **One package = one asset.**

### 2.3 Create the package skeleton
```
agent_<slug>/
├── ROADMAP.md                 ← cp templates/02_ROADMAP_TEMPLATE.md
└── <package>/
    ├── model/
    ├── renders/
    └── README.md              ← cp templates/01_MODEL_README_TEMPLATE.md
```

### 2.4 Model, material, light
Follow STANDARDS.md §2–§5 and `docs/RENDER_SPEC.md`. Recommended headless Blender recipe —
including a camera/light rig script that guarantees the required views — is in
[`docs/WORKFLOW_BLENDER.md`](./docs/WORKFLOW_BLENDER.md).

### 2.5 Render and **look at the results**
- Produce at least 5 images at ≥ 1600×1600 following the required view list.
- Open every image. Open the contact sheet from `tools/make_render_sheet.py`.
- Common failures to look for: clipped extremities, camera inside the mesh, floating parts, lighting
  from behind only, noisy shadows, banding in the gradient background, texture seams, mirrored text.
- Iterate until the set is presentable. Mark rejected renders as discarded — do not commit them.

### 2.6 Write `<package>/README.md`
Copy the template and fill **every** section. Required content is defined in
[`docs/MODEL_SPEC.md`](./docs/MODEL_SPEC.md). Embed renders inline:

```markdown
![Hero three-quarter view](renders/01-hero-three-quarter.png)
```

> Use relative paths without a leading slash. GitHub renders these in the file view and in PRs.

### 2.7 Export the deliverables

**`.glb`** — one file, self-contained:
- Apply modifiers, apply scale, +Y up, correct units, PBR materials, embedded textures.
- Verify with `python tools/check_glb.py agent_<slug>/<package>/model/<package>.glb`.
- Load it somewhere (Blender import, https://gltf-viewer.donmccurdy.com, or any viewer) and confirm
  it looks like your render. **A `.glb` you have not re-imported is not verified.**

**`.blend`** — the editable source:
- Packed textures, no external absolute paths (`File > External Data > Pack Resources`).
- Scene cleaned: only the asset + (optional) render rig on a separate collection.
- Save with compression if it helps keep under the size cap.

### 2.8 Build `renders.zip`
- Flat archive of the PNGs in `renders/`, filenames identical.
- ≥ 5 images, size ≤ 80 MB, no macOS `__MACOSX` entries (use `-x '.*'`).
- Verify: `unzip -l renders.zip`.

### 2.9 Run preflight
```bash
python tools/preflight.py agent_<slug>
```
It checks layout, naming, render count/dimensions, zip integrity, README completeness, GLB sanity,
file-size limits, and forbidden files. **Exit 0 is required.** If you believe a check is wrong, open
an issue against `tools/` — do not bypass it by editing the checker in your PR.

### 2.10 Close the WANTED.md line
```bash
python tools/wanted.py --done <number> --package agent_<slug>/<package>
git add WANTED.md agent_<slug> && git commit -m "feat(<package>): done"
```

### 2.11 Commit and open a PR
```bash
git checkout -b agent_<slug>/<package>
git add agent_<slug>
git commit -m "feat(<package>): add <asset>, <category>, <tris> tris"
git push -u origin agent_<slug>/<package>
```

**Commit message convention** (Conventional Commits):
- `feat(<package>):` new model or new major asset in a package
- `fix(<package>):` corrected geometry, materials, renders, or docs
- `docs(<package>):` README/notes only
- `chore(<workspace>):` roadmap, tooling notes, housekeeping

**PR title:** `feat(<package>): <Asset Name>`
**PR body must include:** package path, **the WANTED.md line you built**, category, triangle count, render count,
preflight output, and an honest note about anything you could not meet.

---

## 3. Branching and parallel work

- Branch name: `agent_<slug>/<package>` (or `agent_<slug>/<package>-fix2` for follow-ups).
- One package (or one coherent milestone) per PR. Do not bundle three unrelated packages.
- Never force-push. Never rebase someone else's branch. Never push to `main` unless explicitly told
  to by the repo owner for that specific action.
- If you have direct write access via a token, still prefer PRs — CI runs there and reviewers can
  see the diff. If you were explicitly instructed to push directly, verify CI on `main` afterwards.

---

## 4. What CI checks

`.github/workflows/validate.yml` runs on every push and PR that touches `agent_*/**`:

1. `tools/preflight.py` over every changed workspace — must exit 0.
2. `tools/check_glb.py` on every `.glb` found — must report a valid, non-empty, in-budget mesh.
3. File-size and forbidden-file checks.
4. The model index in the root README is regenerated and must be in sync (or an agent with the
   `repo-maintainer` role regenerates it).

A red CI is a hard stop. Fix it; don't retry it.

---

## 5. Review checklist (self-review before pushing)

Copy [`docs/REVIEW_CHECKLIST.md`](./docs/REVIEW_CHECKLIST.md) into the bottom of your package README
and tick every box. A reviewer (human or agent) will re-run it. Unchecked boxes or dishonest ticks
are grounds for rejection.

---

## 6. Frequently asked (by agents)

**Q: Can I put several models in one folder?**
No. One asset per package folder. Multiple packages per workspace is fine (and encouraged).

**Q: My environment has no GPU / no Blender. Can I still contribute?**
Yes, if you can produce a valid `.glb` and PNG renders by another route (e.g. a headless three.js
renderer, a Python offline rasteriser). The standards apply to the *output*, not the tool. State the
toolchain in the README.

**Q: Can I use an HDRI from the internet?**
Only with a licence that permits redistribution, and you must credit it in the README. CC0 HDRIs
(Poly Haven, etc.) are acceptable. When in doubt, use a procedural studio setup.

**Q: Can I commit the reference photos I used?**
No, unless you hold the rights. Describe them and link instead. Small, clearly-licensed diagram
crops may be placed in `reference/` **with a credit and licence line** — but it's optional and
generally better to avoid.

**Q: My model is 300 MB.**
Then it does not ship as one file. Decimate, drop LODs, reduce texture resolution, or split the
package. Hard cap is 60 MB per file.

**Q: The preflight complains about render dimensions but my renders look great.**
Re-render at the required size. The checker is not negotiable; presentation standards are part of
the deliverable.

**Q: Do I need to update the root README table?**
No. Leave the generated block alone; the tooling/maintainer owns it.
