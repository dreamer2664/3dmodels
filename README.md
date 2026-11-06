# 3dmodels

A curated repository of original, production-grade 3D assets — each one authored from scratch,
rendered, visually verified, and documented by an autonomous agent.

**There is no "good enough" here.** Every model in this repo must be good enough to drop into a
game, a product visual, or an architectural scene without anyone asking "where did this come from?".
If a corner is cut, the PR does not merge.

> 🛑 **AGENT: READ THIS FIRST.** If you are an AI agent that was told "go to the repo `3dmodels`,
> make a folder called `agent_something`, and make some models" — do **not** start modelling yet.
> Read, in this order:
>
> 1. [`AGENTS.md`](./AGENTS.md) — your operating contract, workspace layout, and the definition of done. **(mandatory)**
> 2. [`CONTRIBUTING.md`](./CONTRIBUTING.md) — the exact step-by-step procedure for submitting a model.
> 3. [`STANDARDS.md`](./STANDARDS.md) — the technical quality bar every asset is measured against.
> 4. [`docs/MODEL_SPEC.md`](./docs/MODEL_SPEC.md) — required content of each model's `.md` write-up
>    (worked example: [`docs/EXAMPLE_PACKAGE_README.md`](./docs/EXAMPLE_PACKAGE_README.md)).
>
> Then run `python tools/preflight.py <your-folder>` before you push. **Preflight failing = you are not done.**
>
> The exact prompt to hand an agent — and how every vague phrase in it maps to a checkable
> requirement — is in [`AGENT_PROMPT.md`](./AGENT_PROMPT.md).

---

## What belongs in this repo

Each contribution is one **agent workspace** containing one or more **model packages**.

| Term | Meaning |
| --- | --- |
| **Agent workspace** | Top-level folder named `agent_<slug>` — owns everything one agent produced. Never shared, never edited by another agent. |
| **Model package** | Subfolder of a workspace named in `kebab-case` after the asset (e.g. `brass-portable-lantern`). Contains the mesh, the renders, the render archive, and the write-up. |
| **Render archive** | `renders.zip` — the 5+ best renders of the finished model, at least one of each required view. |

```
agent_<slug>/                    ← your workspace, one per agent
└── <model-name>/                ← one model package per asset
    ├── renders.zip              ← REQUIRED: 5+ curated renders (the deliverable everyone opens)
    ├── README.md                ← REQUIRED: what the model depicts (see docs/MODEL_SPEC.md)
    ├── model/
    │   ├── <model-name>.glb     ← REQUIRED: the shippable mesh
    │   ├── <model-name>.blend   ← REQUIRED: the editable source
    │   └── textures/            ← optional, only if the asset uses textures
    └── renders/                 ← REQUIRED: the same images that are inside renders.zip
```

A folder that is missing `renders.zip`, missing its `.md`, missing the mesh, or that hands in
unedited default-cube renders will be rejected without discussion. See [`AGENTS.md` § Definition of Done](./AGENTS.md#definition-of-done).

---

## Quality bar at a glance

| Requirement | Target |
| --- | --- |
| Silhouette | Readable and unmistakable at 256 px from 3/4 view; no floating/detached parts |
| Topology | Deliberate, uniform-density, no ngons on deforming/curved surfaces, manifold |
| Scale | Real-world metric, correct up-axis (+Y up in glTF/USD exports), origin at ground centre |
| Materials | All PBR, physically plausible roughness/metalness, no pure-white/black base colours |
| UVs | Unwrapped, non-overlapping, correct texel density (textured assets only) |
| Renders | 1600×1600 minimum, 5+ curated, no clipping, full model in frame, correct colour management |
| Write-up | Complete `README.md` from the spec template, with honest limitations listed |
| Cleanliness | No default objects, no loose geometry, sensible naming, no >60 MB blobs |

Full numbers and per-category rules: [`STANDARDS.md`](./STANDARDS.md).

---

## Repository map

```
README.md                  ← you are here: what this repo is and how to start
AGENT_PROMPT.md            ← drop-in kickoff prompt + prompt→requirement mapping
AGENTS.md                  ← operating contract for autonomous agents (READ FIRST)
CONTRIBUTING.md            ← step-by-step submission procedure
STANDARDS.md               ← technical + visual quality standards
CODE_OF_CONDUCT.md         ← collaboration rules between parallel agents
docs/
  MODEL_SPEC.md            ← required content of every model's README.md
  RENDER_SPEC.md           ← required cameras, lighting, and framing for renders
  WORKFLOW_BLENDER.md      ← how to author + dump cameras/renders headless in Blender
  REVIEW_CHECKLIST.md      ← reviewer/agent self-review gate
  EXAMPLE_PACKAGE_README.md ← fully filled example: the depth expected of a real package
templates/
  00_AGENT_WORKSPACE_TEMPLATE.md
  01_MODEL_README_TEMPLATE.md
  02_ROADMAP_TEMPLATE.md
tools/
  preflight.py             ← local validator: run before every push
  check_glb.py             ← GLB/GLTF inspector (meshes, materials, textures, bounds)
  make_render_sheet.py     ← builds a contact sheet so you can eyeball every render at once
.github/workflows/validate.yml  ← CI gate; blocks any PR that breaks the standards
```

---

## Index of models

Maintained by the repo owner. Agents must **not** edit this table; it is regenerated from the
packages on disk (see `tools/preflight.py --index`).

<!-- MODELS:START -->
| Model | Category | Workspace | Package | Renders |
| --- | --- | --- | --- | --- |
| _no models yet_ | | | | |
<!-- MODELS:END -->

---

## Rules of the road (short version)

1. **Never touch another agent's folder.** No edits, no refactors, no "while I was in there".
2. **One package = one asset.** Don't dump three unrelated models into one folder.
3. **Verify your renders with your own eyes** (open the image, look at it) before you push. A
   render you did not look at is not a render.
4. **Describe honestly.** If the asset is a stylised interpretation, say so. If topology is
   game-ready rather than sub-D, say so. False claims are worse than limitations.
5. **Push to a branch, open a PR.** `main` is protected by CI; direct pushes of unreviewed work
   are not welcome.
6. **Licence:** everything submitted is released under [CC BY 4.0](./LICENSE) unless the package
   README explicitly states otherwise.
