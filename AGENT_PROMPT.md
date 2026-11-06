# AGENT_PROMPT.md — the kickoff prompt

> The original prompt an agent receives is one paragraph. On its own it leaves gaps; this repo fills
> them. Below is the **drop-in prompt** to send to an agent (paste it verbatim), followed by the
> **interpretation table** showing how each vague phrase in the original has been turned into a
> checkable requirement.

---

## 1. Drop-in prompt (paste this to your agent)

Everything between the lines is the message. Replace `<PASTE_PAT_HERE>` with the token.
**If you want a specific asset**, see §1b — that variant also tells the agent what to build.

```
You are an autonomous agent contributing 3D models to https://github.com/dreamer2664/3dmodels

## Credentials
A GitHub fine-grained personal access token for this repo is provided below. I grant you
explicit permission to use it to clone, commit, push branches and open pull requests in
this repository. You do not need to ask me for permission for any git operation.
Never commit the token, never write it into a file inside the repo, and never print it in
a PR body or README. Read it from the environment variable GH_TOKEN.

GH_TOKEN=<PASTE_PAT_HERE>

## Read first (binding documents, in this order)
1. AGENTS.md            - operating contract, folder layout, definition of done
2. BRIEFS.md            - what you are building and how to claim it
3. docs/NO_STOPPING.md  - you must finish the model in ONE run: no stopping, no partial packages
4. docs/SETUP.md        - how to install the toolchain; run tools/setup_blender.sh
5. STANDARDS.md         - the quality bar (this is demanding on purpose)
6. docs/MODEL_SPEC.md   - what the model README must contain
7. docs/RENDER_SPEC.md  - required views, lighting, framing
Do not ask me about scope, style, colour, detail level or camera angles. Those documents decide.

## What to build
Get your assignment from the brief queue - do not invent your own subject:
    python tools/claim_brief.py --next --agent <your-slug>
That assigns you the next open brief, locks it to you, and creates your package folder.
Build exactly the asset that brief describes: its slug, title, dimensions, must_have list
and avoid list are binding. If there is no brief, generate one from a pack
(python tools/brief_from_pack.py packs/basic-props.pack --count 1) or write one with
--new and fill in every field. When the package is pushed, close the loop:
    python tools/claim_brief.py --deliver <brief-id> --agent <your-slug>

## Toolchain: install it, do not report it missing
The sandbox will not have Blender preinstalled. That is expected and it is your job to fix:
    bash tools/setup_blender.sh
    source ~/.local/blender/activate.sh
    blender --version        # must print a version
The script downloads Blender 4.2 LTS, resolves missing shared libraries without root, and
verifies it runs. Use Cycles on CPU (EEVEE has no GPU surface in a sandbox).
"There is no Blender in this sandbox" is not an acceptable report. Only "setup_blender.sh
failed with <exact error> after <these steps>" is, and only after you have pasted its output.

## Non-negotiable: finish in one go
You have many hours available and you are expected to use them. A package is either complete
or it does not exist. Do not end your run with:
  - fewer than 5 renders, or renders under 1600x1600, or a missing renders.zip
  - a missing .glb or a missing .blend
  - a README with TODOs or missing sections
  - a model still at blockout level, or "I'll continue in the next session"
Keep iterating until `python tools/preflight.py agent_<your-slug>` exits 0 and the branch is
pushed. Stopping early is treated as a failed run, not as partial credit. If something breaks,
work down the exhaustion ladder in docs/NO_STOPPING.md section 3 - install, retry, reduce
render cost, simplify the asset. Never abandon the deliverables.

## Your task
- Create your own workspace at the repo root: agent_<your-slug> (lowercase, e.g. agent_atlas).
  Never modify another agent's workspace or any shared file.
- Inside it create one subfolder per model, kebab-case, named after the asset
  (e.g. brass-portable-lantern). One folder = one asset.
- Build the model from scratch at real-world metric scale with clean deliberate topology,
  bevels on every hard edge, believable PBR materials. No downloaded or AI-generated meshes.
- Render the required set with the provided rig:
    blender -b model/<name>.blend --python tools/render_rig.py -- --res 1600 --samples 96 --out renders
  That produces hero 3/4, front, side, back, top, detail, plus a wireframe and a 1 m scale
  reference, and it prints a framing check (every view must report margin >= ~4%).
- LOOK AT EVERY RENDER BEFORE YOU PUSH. Open each image. Inspect it. Iterate until the set is
  presentable. Build the contact sheet (tools/make_render_sheet.py) and inspect that too.
  Renders you have not opened do not count.
- Deliver: renders/ + renders.zip (>=5 images, flat archive, <80 MB), model/<name>.glb
  (self-contained, re-imported and verified), model/<name>.blend (packed, clean scene,
  no default objects), README.md from templates/01_MODEL_README_TEMPLATE.md with an honest
  Limitations section.
- Run `python tools/preflight.py agent_<your-slug>` and fix everything until it exits 0.
- Push to branch agent_<your-slug>/<package> and open a PR with the preflight output pasted in:
    git remote add origin "https://x-access-token:${GH_TOKEN}@github.com/dreamer2664/3dmodels.git"

Never invent results, never claim a check you did not run, never commit a secret.
Your final message must answer the five self-audit questions in docs/NO_STOPPING.md section 6.
```

## 1b. Variant — you want one specific asset, not the queue

Say the subject in the prompt. Everything else stays identical (read the same docs, same standards,
same one-run rule); the only difference is the asset is specified by you instead of by the queue.

```
You are an autonomous agent contributing to https://github.com/dreamer2664/3dmodels
GH_TOKEN=<PASTE_PAT_HERE>     # owner grants permission to use this token for git operations

[first two paragraphs of the prompt in §1: read-first list + toolchain install]

## What to build — this asset, exactly
  Asset      : late-19th-century brass portable oil lantern
  Slug       : brass-portable-lantern      (folder + package + file names)
  Category   : hard-surface-prop
  Dimensions : 16.2 cm wide, 16.2 cm deep, 31.2 cm tall (real-world metres)
  Style      : stylised-realistic, game-ready PBR
  Must have  : flared spun-brass base with rolled seam; domed vent cap with louvres and a
               lifting loop; four glass guard wires; hinged side door with a visible hinge pin;
               wire bail handle as a separate posable object; knurled wick adjuster knob
  Avoid      : soot, heavy damage, legible branding, a lit flame
  Tri budget : 20k-80k
  References : museum photos of railway hand lanterns (form and proportion only)

Treat this as brief #0: it overrides the brief queue. Create agent_<your-slug>/brass-portable-lantern/,
record `brief_source: prompt` in the package README front-matter, and skip
`claim_brief.py --next`. Everything else - one run, 5+ renders at 1600px, zip, README, preflight
exit 0, branch + PR - is unchanged and non-negotiable.
```

Keep the field list to what you actually care about. A prompt with **dimensions + must_have + avoid**
produces a dramatically more predictable model than three paragraphs of adjectives.

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
| "they say there's no blender in the sandbox" | `docs/SETUP.md` + `tools/setup_blender.sh`: one-command no-root install (Blender 4.2 LTS tarball, shared-library autopair via `apt-get download`), verified end-to-end in a clean sandbox; "not installed" is explicitly an unacceptable report |
| "they stop halfway" | `docs/NO_STOPPING.md`: one-run rule, list of violations, completion loop, 10-rung exhaustion ladder, credentials pre-granted, time budget, and a 5-question self-audit that must be answered in the final message |
| "how does the agent know what to build?" | `BRIEFS.md` + `BRIEFS/OPEN/` queue with atomic claims (`tools/claim_brief.py --next`), themed `packs/`, `brief #0` in the prompt for one-off subjects, and `BRIEFS/DELIVERED/` as the audit trail |
| (implicit) "they need push access" | PAT placeholder in `.env.example` and in the prompt above, with the owner's explicit written permission to use it; token kept out of the repo tree by `.gitignore` |
| (implicit) "don't collide with other agents" | `CODE_OF_CONDUCT.md`, branch/staging rules, CI guard that rejects PRs touching shared files |

---

## 3. What the agent *should not* need to ask you

- Which model to make → **it is assigned one** by the brief queue (`BRIEFS.md`); it never invents a subject while briefs exist.
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
