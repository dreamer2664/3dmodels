# NO_STOPPING.md — finish the model in one run

This file exists because agents stop early. Not because a model takes too long — you can run for tens
of hours — but because stopping is *easy*: the .blend saved, the first render looked fine, the README
is half-written, and the turn ends. Then nothing gets finished.

**A package is either complete or it does not exist.** Partial work in `main` is a liability. It looks
like a finished asset until someone opens it.

---

## 1. The one-run rule

> **Everything a package needs is produced in a single working session: model, materials, renders,
> zip, README, validation, push. You do not stop between steps, and you do not stop until
> `tools/preflight.py` exits 0 and the branch is pushed.**

A "working session" is your entire available run. You are explicitly authorised to run for many hours.
The correct amount of work before you stop is *all of it*.

### What counts as stopping early (all are violations)

- Ending the turn with a package that has no `renders.zip`.
- Ending the turn with `renders/` holding 2–4 images and a note that you'll "add the rest later".
- Shipping a `.glb` but no `.blend`, or vice versa.
- A README with sections marked "coming soon", "TBD", or omitted.
- A model with your blockout shapes still in it, at whatever detail you happened to reach.
- Renders at 800×800, or 1600×1600 with the model cropped and "will fix framing next run".
- Any message that means "I'll continue in the next session" while the package is incomplete.
- Stopping because a render took longer than expected, because Blender wasn't preinstalled, because a
  library was missing, or because the task "is large".
- Deleting the package you started instead of finishing it.

### What is *not* stopping early

- Pushing a **complete** package, then wanting to improve it — that is a new PR (`fix(<package>): …`).
- Reporting a genuine blocker **after** exhausting §3 below, while leaving no half-built package in
  the branch (push nothing, or push on a clearly-named `wip/` branch you do not open a PR from).

---

## 2. The completion loop (do not exit until it is green)

```
  ┌─> build/refine model
  │
  ├─> materials
  │
  ├─> render the full set (render_rig.py)
  │
  ├─> LOOK at every render + the contact sheet
  │        │
  │        └─ problems? ──> fix geometry/material/lighting ──┐
  │                                                          │
  ├─> export .glb, re-import it, compare with renders        │
  │                                                          │
  ├─> write README (all sections, honest limitations)        │
  │                                                          │
  ├─> zip renders, run preflight  ──── errors? ──────────────┘
  │        │
  │        └─ clean (exit 0)
  │
  ├─> push branch + open PR
  │
  └─> done. THEN you may stop.
```

**Iteration is expected.** Two render passes is normal; five is fine. What is not fine is one pass and
a shrug. If a render is visibly wrong, you have not finished — you have a draft, and drafts are not
allowed to be the last thing you do.

---

## 3. Exhaustion ladder — try all of this before saying you are blocked

Work down the list. Only after the last rung is a blocker real.

| # | Blocker | Do this first |
| --- | --- | --- |
| 1 | "No Blender in the sandbox" | `bash tools/setup_blender.sh` ([SETUP.md](./SETUP.md)). It downloads and installs it in ~20 s without root. |
| 2 | "Missing shared library" (`libxkbcommon.so.0`, `libGL.so.1`, …) | the setup script resolves these with `apt-get download` + `dpkg-deb -x`; if one is left, add it to `pkg_for()` and re-run |
| 3 | "EEVEE fails / no GPU" | use Cycles CPU: `--engine CYCLES` (the default in `render_rig.py`). Measured ~30–60 s per 1600² view on 2 cores. |
| 4 | "Renders are slow" | drop `--samples` to 64–96, resolution to 1600, and raise it only for the hero shot. Never drop views. |
| 4b | "Blender exits 137 / render produces no file" | that is the OOM killer, not a broken scene: OpenImageDenoise needs ~1.2 GB at 1600². Re-run with `--no-denoise` (the rig then post-denoises), and if it still dies, batch views (`--views 01,02,03`) or drop samples to 24. See SETUP.md §3. |
| 4c | "Renders are too slow" | 1600²/96 with denoise is ~45 s/view when RAM allows; the low-RAM path is ~4 min/view (~35 min for the set). Both are minutes, not hours. Batch with `--views`, iterate at 700²/48 (~3 min for six views) and do the final pass at 1600². |
| 5 | "Out of disk in /tmp" | extract Blender to `$HOME/.local/blender` (the script already does), and write renders under the repo, not `/tmp` |
| 6 | "Out of disk overall" | downscale textures to 1–2K, apply modifiers, decimate, delete `.blend1` backups, clear Blender's cache |
| 7 | "The model is too complex to finish" | reduce scope of the *asset*, not of the *deliverable set*: a simpler object finished properly beats an ambitious object left half-finished. Pick a smaller hero prop on the next run; for this one, finish what you scoped. |
| 8 | "A tool call failed / timed out" | re-run it, split it into smaller steps, add `--samples`/`--res` reductions, log to a file and read the tail. Timeouts are not verdicts. |
| 9 | "I don't know what the user wants stylistically" | the standards decide: stylised-realistic, game-ready PBR, metric. Decide and document. |
| 10 | "Push failed" | check the token (§4), check the branch name, `git pull --rebase`, retry with `--verbose`. Report the HTTP error if it still fails. |

Only if you reach the bottom of that ladder **and** have captured exact command output may you report
a blocker — and even then, the report must say what *is* delivered and what exactly is missing.

---

## 4. Permission and credentials (explicit, pre-granted)

- **You have the repo owner's explicit permission to push to this repository** using the
  `GH_TOKEN` / PAT configured in your environment (see [AGENT_PROMPT.md](../AGENT_PROMPT.md) §3 —
  the owner has placed a PAT placeholder there and states permission is granted for agent use).
- You do **not** need to ask for confirmation before: creating branches, committing, pushing,
  opening PRs, installing packages, downloading CC0 HDRIs, or running long renders.
- **Never** commit the token, echo it into a file, or paste it into a README, render metadata, or PR
  body. Read it from the environment: `$GH_TOKEN` (or `$GITHUB_TOKEN`).
- If the token is absent or rejected, say exactly what failed (`HTTP 401/403` and the remote URL
  without the token) and continue with everything that does not require pushing — including
  finishing the package locally. Do not abandon the model because the push failed.

Push pattern that always works with a PAT:

```bash
git remote add origin "https://x-access-token:${GH_TOKEN}@github.com/dreamer2664/3dmodels.git"
git checkout -b agent_<slug>/<package>
git add agent_<slug>
git commit -m "feat(<package>): add <asset>"
git push -u origin agent_<slug>/<package>
```

---

## 5. Budget guidance (so "long" is not a surprise)

A compliant hard-surface prop at 1600², Cycles CPU, 2 cores:

| Step | Realistic time |
| --- | --- |
| install Blender | ~20 s (once) |
| modelling + materials | 2–6 h of agent iterations |
| 6 views at 1600² / 96 samples | 5–8 min |
| extra passes (wireframe, scale ref) | +2 min |
| re-render after fixes ×2–3 rounds | 15–30 min |
| export, verify glb, README, zip, preflight | 15–20 min |
| **total** | **a few hours, not tens** |

You have far more time than this. Running out of *patience* is not running out of *time*. If you find
yourself with hours left and a package that is "good enough", that is the signal to make the third
render pass, add the detail pass, and fix the framing — not to stop.

---

## 6. Self-audit before you end the turn

Answer these honestly in your final message. Any "no" means you are not done:

1. Does `agent_<slug>/<package>/` contain `model/*.glb`, `model/*.blend`, `renders/` (≥ 5 PNGs,
   ≥ 1600²), `renders.zip`, `README.md`? **yes / no**
2. Did I open every render and the contact sheet, and iterate at least twice? **yes / no**
3. Did `python tools/preflight.py agent_<slug>` exit 0? (paste the final lines) **yes / no**
4. Is the PR open with the preflight output in the body? **yes / no**
5. Did I leave any TODO/TBD/placeholder, or any package in a half-built state? **yes / no**

If the answer to (5) is yes, keep working. There is no version of this task where stopping there is
correct.
