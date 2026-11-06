# AGENT_PROMPT.md — the kickoff prompt

> The original prompt an agent receives is one paragraph. On its own it leaves gaps; this repo fills
> them. Below is the **drop-in prompt** to send to an agent (paste it verbatim), followed by the
> **interpretation table** showing how each vague phrase in the original has been turned into a
> checkable requirement.

---

## 1. Drop-in prompt (paste this to your agent)

```
You are contributing 3D models to the repository https://github.com/dreamer2664/3dmodels .

Before you create anything, read these files in order and treat them as binding:
  1. AGENTS.md               (operating contract, folder layout, definition of done)
  2. STANDARDS.md            (technical and visual quality bar)
  3. CONTRIBUTING.md         (exact step-by-step procedure)
  4. docs/MODEL_SPEC.md      (what the package README must contain)
  5. docs/RENDER_SPEC.md     (required camera views, lighting, framing)
  6. templates/01_MODEL_README_TEMPLATE.md
Do not ask me questions about scope, style, colour or detail level — the documents decide those.

Your task:
  - Create your own workspace folder at the repo root named "agent_<your-slug>" (lowercase, e.g.
    agent_atlas). Never modify another agent's workspace or any shared file.
  - Inside it, create one subfolder per model, named in kebab-case after the asset
    (e.g. brass-portable-lantern). One folder = one asset.
  - Build the model from scratch at real-world metric scale, with clean deliberate topology,
    believable PBR materials and bevels on every hard edge. No downloaded or AI-generated meshes.
  - Render at least 5 images at 1600x1600 or larger, covering the entire model with an 8-12% margin:
    hero three-quarter, front, side, back, top, plus a detail or wireframe shot. Three-point lighting,
    opaque neutral background, contact shadow, no clipping, no noise.
  - LOOK AT EVERY RENDER BEFORE YOU PUSH. Open the images, inspect them, and iterate until they are
    presentable. A render you have not opened does not exist. Build the contact sheet with
    tools/make_render_sheet.py and inspect that too.
  - Put the curated renders in renders/ AND in a flat renders.zip (at least 5 images, under 80 MB).
  - Ship model/<name>.glb (self-contained, re-imported and verified) and model/<name>.blend
    (packed textures, clean scene, no default objects).
  - Write <package>/README.md from templates/01_MODEL_README_TEMPLATE.md, filling every section,
    including an honest Limitations section. No TODO, TBD or placeholder text.
  - Run `python tools/preflight.py agent_<your-slug>` and fix everything until it exits 0.
  - Push to a branch named agent_<your-slug>/<package> and open a PR using the repo's PR template
    with the preflight output pasted in. Do not push unreviewed work to main.

If something in the standards is impossible in your environment, ship what you can, say exactly what
you could not meet in the package README's Limitations section AND in the PR description, and
continue. Never invent results, never claim a check you did not run, and never commit a secret.
```

---

## 2. How the original prompt maps to requirements

| Original phrase | Turned into |
| --- | --- |
| "make 3d models" | One package = one asset; category-specific triangle budgets; quality rubric in `STANDARDS.md` §9 |
| "go to my repo 3dmodels" | Clone → branch `agent_<slug>/<package>` → PR; never push to `main` unreviewed |
| "make your folder with a name `agent_something`" | `agent_<slug>` naming regex, enforced by `tools/preflight.py` and CI; one owner per workspace; no edits outside it |
| "another subfolder with the name of the first 3d models you'll make" | `<package>/` in kebab-case matching the asset name; files named after the package; `ROADMAP.md` for the backlog |
| "real quality" | `STANDARDS.md`: manifold geometry, no ngons on curves, bevels, real-world metric scale, PBR values, texel density, honest docs; scoring rubric with a pass threshold |
| "a zip of the best renders" | `renders.zip` required, flat, ≥ 5 images, < 80 MB, must match `renders/` exactly — checked automatically |
| "at least 5, capturing the whole model" | ≥ 5 PNGs at ≥ 1600×1600 with 8–12 % margin, full model in frame, no clipping; required view list (hero 3/4, front, side, back, top, detail) |
| "the actual 3d model" | Required deliverables: `<package>.glb` (shippable, re-imported and verified) and `<package>.blend` (editable source, packed textures); `tools/check_glb.py` inspection |
| "a .MD file explaining what the model depicts" | `<package>/README.md` from `templates/01_MODEL_README_TEMPLATE.md`; required sections and depth defined in `docs/MODEL_SPEC.md`; no placeholders allowed |
| "Look at the renders before pushing" | Mandatory self-inspection protocol (`docs/RENDER_SPEC.md` §6), contact-sheet review step, ticked checklist in the README, "gaps" field in the PR template |
| (implicit) "don't collide with other agents" | `CODE_OF_CONDUCT.md`, branch/staging rules, CI guard that rejects PRs touching shared files |

---

## 3. What the agent *should not* need to ask you

- Which model to make → it picks a specific, referenceable, iconically shaped asset and records it in `ROADMAP.md`.
- Realistic or stylised → stylised-realistic / game-ready PBR by default, declared in the README.
- Units, scale, origin → metric metres, origin at ground centre, +Y up on export.
- Poly budget → per-category table in `STANDARDS.md` §1.
- Number of renders, resolution, camera angles, lighting → `docs/RENDER_SPEC.md`.
- README structure and depth → `docs/MODEL_SPEC.md` + template + a fully worked example in `docs/EXAMPLE_PACKAGE_README.md`.
- How to render headless → `docs/WORKFLOW_BLENDER.md` (complete copy-paste script).
- Where to push, how to name the branch, what the PR must contain → `CONTRIBUTING.md` + PR template.

## 4. What you *will* still be asked about (deliberately)

- Permission when the environment cannot push or CI is broken for unrelated reasons.
- Approval for a policy change to the shared standards (a dedicated PR, not a bypass).
- Anything requiring licensed third-party data (an HDRI, a scanned reference, a branded design).
